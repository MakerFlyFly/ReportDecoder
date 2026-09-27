#!/usr/bin/env python3
"""Build and verify the installable skill, with an explicit file allowlist."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
import zipfile

from validate_project import validate_skill


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "research-report-reader"
FILES = [
    "SKILL.md", "USAGE.md", "VALIDATION.md",
    "assets/note-template.md", "references/analysis-rules.md", "references/examples.md",
    "scripts/pdf_tools.py", "tests/test_pdf_tools.py", "tests/fixtures/build_fixtures.py",
    "tests/fixtures/synthetic-report.pdf", "tests/fixtures/blank-middle.pdf",
    "tests/fixtures/image-only.pdf", "tests/fixtures/password-protected.pdf", "tests/fixtures/broken.pdf",
]


def build_payload():
    validate_skill(SKILL)
    entries = {}
    for relative in FILES:
        raw = (SKILL / relative).read_bytes()
        if not relative.endswith(".pdf"):
            raw = raw.replace(b"\r\n", b"\n")
        entries["research-report-reader/" + relative] = raw
    entries["research-report-reader/LICENSE"] = (ROOT / "LICENSE").read_bytes().replace(b"\r\n", b"\n")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    payload = buffer.getvalue()
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ValueError("Archive integrity or member check failed")
        if any(archive.read(name) != data for name, data in entries.items()):
            raise ValueError("Archive does not match the selected source files")
        with tempfile.TemporaryDirectory(prefix="reportdecoder-install-") as temp:
            archive.extractall(temp)  # Entries are constructed above, never taken from an input archive.
            validate_skill(Path(temp) / "research-report-reader")
    return payload, len(entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--force", action="store_true", help="Replace a different local, unpublished build")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version) is None:
        parser.error("VERSION must contain a semantic version")
    payload, members = build_payload()
    directory = args.output_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / ("research-report-reader-v" + version + ".zip")
    if destination.exists() and destination.read_bytes() != payload and not args.force:
        parser.error("A different archive already exists; use --force only for an unpublished local rebuild")
    destination.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    sums = directory / "SHA256SUMS"
    sums.write_text(digest + "  " + destination.name + "\n", encoding="ascii")
    print(json.dumps({"archive":str(destination),"sha256":digest,"checksums":str(sums),"files":members,"bytes":len(payload),"installation_resources_verified":True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
