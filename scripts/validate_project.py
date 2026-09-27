#!/usr/bin/env python3
"""Validate skill resources, public sample provenance, and tracked publication paths."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    "README.md", "LICENSE", "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md",
    ".gitignore", ".gitattributes", "VERSION", "requirements-dev.txt",
}
PUBLIC_DIRS = {"research-report-reader", "samples", "scripts", ".github"}
PRIVATE_PARTS = {".reading-work", ".validation", "outputs", "dist", "tmp", "__pycache__", ".venv", "venv"}
FIXTURE_PDFS = {"synthetic-report.pdf", "blank-middle.pdf", "image-only.pdf", "password-protected.pdf", "broken.pdf"}
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".txt"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def is_public_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or any(p in PRIVATE_PARTS for p in path.parts):
        return False
    if path.name.startswith(".env") or path.suffix.lower() in {".pyc", ".pyo", ".zip"}:
        return False
    return name in ROOT_FILES or (len(path.parts) > 1 and path.parts[0] in PUBLIC_DIRS)


def check_markdown_links(path, boundary):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)\n]+)\)", text):
        target = target.strip().strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or not parsed.path:
            continue
        resolved = (path.parent / unquote(parsed.path)).resolve()
        require(boundary == resolved or boundary in resolved.parents, "Link escapes package: " + str(path))
        require(resolved.is_file() or resolved.is_dir(), "Broken resource link: {} -> {}".format(path, target))


def validate_skill(folder):
    folder = Path(folder).resolve()
    entry = folder / "SKILL.md"
    text = entry.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
    require(match is not None, "Missing SKILL.md YAML frontmatter")
    meta = yaml.safe_load(match.group(1))
    require(isinstance(meta, dict), "Skill frontmatter must be a mapping")
    name = meta.get("name")
    description = meta.get("description")
    require(isinstance(name, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is not None and len(name) <= 64, "Invalid skill name")
    require(name == folder.name, "Skill name must match the folder name")
    require(isinstance(description, str) and 0 < len(description.strip()) <= 1024, "Invalid skill description")
    allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    require(not (set(meta) - allowed), "Unknown skill frontmatter fields")
    require("[TODO:" not in text, "Unfinished skill scaffold")
    for doc in folder.rglob("*.md"):
        check_markdown_links(doc, folder)
    return name


def validate_samples():
    allowed_pdfs = set()
    samples = sorted((ROOT / "samples").glob("*/source.json"))
    require(bool(samples), "A public sample is required")
    for path in samples:
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"title", "publisher", "publication_date", "retrieved_date", "url", "rights_url", "rights_basis", "file", "sha256", "pages", "analysis"}
        require(required <= data.keys(), "Incomplete sample metadata: " + str(path))
        for field in ("file", "analysis"):
            value = data[field]
            require(isinstance(value, str) and Path(value).name == value and value not in {".", ".."}, "Sample paths must be filenames")
        source = path.parent / data["file"]
        analysis = path.parent / data["analysis"]
        raw = source.read_bytes()
        require(raw.startswith(b"%PDF-"), "Sample is not a PDF")
        require(hashlib.sha256(raw).hexdigest() == data["sha256"], "Public PDF hash mismatch: " + str(source))
        require(type(data["pages"]) is int and data["pages"] > 0, "Invalid sample page count")
        require(urlsplit(data["url"]).scheme == "https" and urlsplit(data["rights_url"]).scheme == "https", "Public provenance links must use HTTPS")
        require(bool(data["rights_basis"].strip()), "Sample rights basis is required")
        note = analysis.read_text(encoding="utf-8")
        require("**完成状态**：完整" in note and "整理中" not in note, "Sample analysis is not complete")
        anchors = re.findall(r'<a id="([^"]+)"', note)
        links = re.findall(r"\]\(#([^)]+)\)", note)
        require(len(anchors) == len(set(anchors)) and not(set(links) - set(anchors)), "Broken sample navigation")
        require((path.parent / "README.md").is_file(), "Sample usage and attribution are required")
        allowed_pdfs.add(source.relative_to(ROOT).as_posix())
    return samples, allowed_pdfs


def validate_project(staged=False):
    validate_skill(ROOT / "research-report-reader")
    require(re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", (ROOT / "VERSION").read_text().strip()) is not None, "Invalid VERSION")
    for name in ROOT_FILES:
        require((ROOT / name).is_file(), "Missing publication file: " + name)
    samples, allowed_pdfs = validate_samples()
    allowed_pdfs.update("research-report-reader/tests/fixtures/" + name for name in FIXTURE_PDFS)
    if staged:
        result = subprocess.run(["git", "ls-files", "--cached", "-z"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        paths = [part.decode("utf-8") for part in result.stdout.split(b"\0") if part]
        require(bool(paths), "No files staged or tracked")
        forbidden = [p for p in paths if not is_public_path(p)]
        require(not forbidden, "Non-public paths tracked: " + ", ".join(forbidden))
    else:
        paths = list(ROOT_FILES)
        for directory in PUBLIC_DIRS:
            paths.extend(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob("*") if p.is_file() and is_public_path(p.relative_to(ROOT).as_posix()))
    for name in paths:
        path = ROOT / name
        if path.suffix.lower() == ".pdf":
            require(name in allowed_pdfs, "PDF lacks approved sample provenance or fixture registration: " + name)
        if path.suffix.lower() == ".md":
            check_markdown_links(path, ROOT)
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8")
            require(re.search(r"[A-Za-z]:[\\/](?:Users|AAAGood)[\\/]", text) is None, "Machine-specific personal path in " + name)
    return {"skill": "research-report-reader", "public_samples": len(samples), "files_checked": len(paths), "tracked_paths_checked": staged}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Also reject private paths in Git's index")
    args = parser.parse_args()
    try:
        print(json.dumps(validate_project(args.staged), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print("Validation failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
