#!/usr/bin/env python3
"""Portable PDF preparation for research-report-reader. Python 3.9+, stdlib only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
import uuid


class PdfToolError(Exception):
    def __init__(self, code, message, diagnostic=""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.diagnostic = diagnostic


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def write_json(path, value):
    with Path(path).open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tool_path(name, poppler_dir=None):
    # Native executables avoid cmd.exe interpreting metacharacters in PDF names.
    executable = name + ".exe" if os.name == "nt" else name
    if poppler_dir:
        candidate = Path(poppler_dir).expanduser().resolve() / executable
        found = str(candidate) if candidate.is_file() else None
    else:
        found = shutil.which(executable)
    if not found:
        raise PdfToolError("missing_dependency", "缺少可运行的 Poppler 原生程序：" + name)
    return found


def run_tool(command, timeout):
    env = os.environ.copy()
    env.update({"LC_ALL": "C", "LANG": "C"})
    options = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            [str(part) for part in command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=env,
            shell=False,
            **options
        )
    except subprocess.TimeoutExpired as exc:
        detail = (exc.stderr or b"").decode("utf-8", errors="replace")
        raise PdfToolError("tool_timeout", "PDF 工具调用超时。", detail) from exc
    except OSError as exc:
        raise PdfToolError("tool_unavailable", "PDF 工具无法启动。", str(exc)) from exc
    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode:
        raise PdfToolError(
            "pdf_read_failed",
            "PDF 工具无法读取或处理文件；请检查损坏、访问权限或密码保护。",
            stderr,
        )
    return result.stdout, stderr


def source_file(value):
    source = Path(value).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise PdfToolError("invalid_input", "需要一份存在且可读取的本地 PDF 文件。")
    return source


def page_count(source, pdfinfo, timeout):
    output, warning = run_tool([pdfinfo, "-enc", "UTF-8", source], timeout)
    match = re.search(r"^Pages:\s*(\d+)\s*$", output.decode("utf-8", errors="replace"), re.M)
    if not match or int(match.group(1)) < 1:
        raise PdfToolError("invalid_page_count", "无法确定 PDF 的有效页数。", warning)
    return int(match.group(1)), warning


def new_work_dir(parent=None, prefix="rrr-"):
    if parent is not None:
        parent = Path(parent).expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(parent) if parent else None)).resolve()


def quality_flags(text, warning):
    visible = "".join(text.split())
    flags = []
    if not visible:
        flags.append("no_text")
    elif len(visible) < 50:
        flags.append("sparse_text")
    if "\ufffd" in text or any(ord(char) < 32 and char not in "\n\r\t" for char in text):
        flags.append("encoding_warning")
    if warning.strip():
        flags.append("tool_warning")
    return len(visible), flags


def extract_pdf(pdf, work_dir=None, poppler_dir=None, timeout=60):
    source = source_file(pdf)
    info = tool_path("pdfinfo", poppler_dir)
    totext = tool_path("pdftotext", poppler_dir)
    before = fingerprint(source)
    count, info_warning = page_count(source, info, timeout)
    work = new_work_dir(work_dir)
    (work / "pages").mkdir()
    (work / "diagnostics").mkdir()
    if info_warning.strip():
        (work / "diagnostics" / "pdfinfo.txt").write_text(info_warning, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "source_pdf": str(source),
        "source_sha256": before,
        "page_count": count,
        "status": "extracting",
        "document_flags": ["tool_warning"] if info_warning.strip() else [],
        "pages": [],
    }
    manifest_path = work / "manifest.json"
    # Preserve partial progress if the host interrupts a long report.
    write_json(manifest_path, manifest)
    for page in range(1, count + 1):
        row = {"page": page, "text_file": None, "nonspace_chars": 0, "flags": []}
        try:
            output, warning = run_tool(
                [totext, "-f", page, "-l", page, "-layout", "-enc", "UTF-8", "-eol", "unix", source, "-"],
                timeout,
            )
            text = output.decode("utf-8", errors="replace").replace("\f", "")
            size, flags = quality_flags(text, warning)
            relative = "pages/page-{:04d}.txt".format(page)
            with (work / relative).open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            row.update({"status": "extracted", "text_file": relative, "nonspace_chars": size, "flags": flags})
            if warning.strip():
                (work / "diagnostics" / ("page-{:04d}.txt".format(page))).write_text(warning, encoding="utf-8")
        except PdfToolError as exc:
            row.update({"status": "failed", "flags": ["extraction_failed"], "error_code": exc.code})
            (work / "diagnostics" / ("page-{:04d}.txt".format(page))).write_text(
                exc.message + "\n" + exc.diagnostic, encoding="utf-8"
            )
        manifest["pages"].append(row)
        write_json(manifest_path, manifest)

    if fingerprint(source) != before:
        manifest["status"] = "source_changed"
        write_json(manifest_path, manifest)
        raise PdfToolError("source_changed", "读取期间 PDF 已改变，请重新提取。")

    failed = [row["page"] for row in manifest["pages"] if row["status"] == "failed"]
    review = [row["page"] for row in manifest["pages"] if row["flags"]]
    chars = sum(row["nonspace_chars"] for row in manifest["pages"])
    if len(failed) == count:
        status, code = "failed", 2
    elif failed:
        status, code = "review_required", 3
    elif chars == 0:
        status, code = "no_extractable_text", 4
    elif review or manifest["document_flags"]:
        status, code = "review_required", 3
    else:
        status, code = "extracted", 0
    manifest["status"] = status
    write_json(manifest_path, manifest)
    return {
        "status": status,
        "manifest": str(manifest_path),
        "page_count": count,
        "review_pages": review,
        "failed_pages": failed,
        "document_flags": manifest["document_flags"],
    }, code


def parse_pages(value, count):
    if value.strip().lower() == "all":
        return list(range(1, count + 1))
    pages = set()
    for part in value.split(","):
        match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", part)
        if not match:
            raise PdfToolError("invalid_pages", "页码格式应为 1,3-5 或 all。")
        start, end = int(match.group(1)), int(match.group(2) or match.group(1))
        if start < 1 or end < start or end > count:
            raise PdfToolError("invalid_pages", "页码范围无效或超出 PDF 总页数。")
        pages.update(range(start, end + 1))
    return sorted(pages)


def load_manifest(value):
    path = Path(value).expanduser().resolve()
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise ValueError("schema")
        count = manifest["page_count"]
        if type(count) is not int or count < 1:
            raise ValueError("page count")
        if not isinstance(manifest["source_pdf"], str):
            raise ValueError("source")
        if not re.fullmatch(r"[0-9a-f]{64}", manifest["source_sha256"]):
            raise ValueError("hash")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise PdfToolError("invalid_manifest", "无法读取有效的提取 manifest。") from exc
    source = source_file(manifest["source_pdf"])
    if fingerprint(source) != manifest["source_sha256"]:
        raise PdfToolError("source_changed", "PDF 与提取时的文件不一致，请重新提取。")
    if manifest.get("status") == "source_changed":
        raise PdfToolError("source_changed", "提取期间源文件发生改变，请重新提取。")
    return path, manifest, source


def render_pdf(manifest_file, pages, dpi=144, poppler_dir=None, timeout=60):
    if not 72 <= dpi <= 300:
        raise PdfToolError("invalid_dpi", "DPI 必须在 72 到 300 之间。")
    manifest_path, manifest, source = load_manifest(manifest_file)
    selected = parse_pages(pages, manifest["page_count"])
    topng = tool_path("pdftoppm", poppler_dir)
    work = new_work_dir(manifest_path.parent, prefix="render-")
    rendered, failed = [], []
    for page in selected:
        prefix = work / ("page-{:04d}".format(page))
        try:
            _, warning = run_tool(
                [topng, "-f", page, "-l", page, "-r", dpi, "-singlefile", "-png", source, prefix], timeout
            )
            png = prefix.with_suffix(".png")
            if not png.is_file() or png.stat().st_size == 0:
                raise PdfToolError("render_failed", "页面渲染未产生有效图像。")
            rendered.append({"page": page, "image": str(png)})
            if warning.strip():
                prefix.with_suffix(".log").write_text(warning, encoding="utf-8")
        except PdfToolError as exc:
            failed.append({"page": page, "error_code": exc.code})
            prefix.with_suffix(".log").write_text(exc.message + "\n" + exc.diagnostic, encoding="utf-8")
    if fingerprint(source) != manifest["source_sha256"]:
        raise PdfToolError("source_changed", "渲染期间 PDF 已改变，请重新提取。")
    status = "rendered" if not failed else ("partial" if rendered else "failed")
    summary = {"status": status, "images": rendered, "failed_pages": failed}
    write_json(work / "render-manifest.json", summary)
    return summary, (0 if not failed else (3 if rendered else 2))


def new_note(output_dir):
    directory = Path(output_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for _ in range(100):
        path = directory / ("研报解读-{}-{}.md".format(timestamp, uuid.uuid4().hex[:8]))
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write("# 研报阅读笔记\n\n**完成状态**：整理中\n")
            return {"status": "draft_created", "note": str(path)}, 0
        except FileExistsError:
            continue
    raise PdfToolError("output_collision", "未能分配新的匿名文件名；已有笔记未被覆盖。")


def doctor(poppler_dir=None, timeout=60):
    results = []
    for name in ("pdfinfo", "pdftotext", "pdftoppm"):
        try:
            executable = tool_path(name, poppler_dir)
            run_tool([executable, "-v"], timeout)
            results.append({"tool": name, "available": True})
        except PdfToolError as exc:
            results.append({"tool": name, "available": False, "error_code": exc.code})
    ok = all(row["available"] for row in results)
    return {"status": "ready" if ok else "missing_dependencies", "tools": results}, (0 if ok else 2)


def positive_seconds(value):
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("timeout must be positive and finite")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("doctor", help="Check native Poppler tools")
    extract = sub.add_parser("extract", help="Extract UTF-8 text one physical page at a time")
    extract.add_argument("pdf")
    extract.add_argument("--work-dir", help="Parent of a newly allocated private work directory")
    render = sub.add_parser("render", help="Render selected physical pages using an extraction manifest")
    render.add_argument("--manifest", required=True)
    render.add_argument("--pages", required=True, help="1,3-5 or all")
    render.add_argument("--dpi", type=int, default=144)
    reserve = sub.add_parser("new-note", help="Create an anonymous draft without overwriting files")
    reserve.add_argument("--output-dir", default="outputs")
    for command in (check, extract, render):
        command.add_argument("--poppler-dir", help="Directory containing native Poppler executables")
        command.add_argument("--timeout", type=positive_seconds, default=60)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result, code = doctor(args.poppler_dir, args.timeout)
        elif args.command == "extract":
            result, code = extract_pdf(args.pdf, args.work_dir, args.poppler_dir, args.timeout)
        elif args.command == "render":
            result, code = render_pdf(args.manifest, args.pages, args.dpi, args.poppler_dir, args.timeout)
        else:
            result, code = new_note(args.output_dir)
    except PdfToolError as exc:
        result, code = {"status": "error", "error_code": exc.code, "message": exc.message}, 2
    except (OSError, UnicodeError):
        result, code = {
            "status": "error", "error_code": "filesystem_error",
            "message": "无法读取或写入所需文件；请检查路径、访问权限与可用空间。",
        }, 2
    emit(result)
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
