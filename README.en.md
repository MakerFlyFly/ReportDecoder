# ReportDecoder

[简体中文](README.md) · English

**Follow the evidence and reasoning in a research report.**

ReportDecoder is a Codex and Claude Code skill for reading financial and economic research PDFs. It produces English or Simplified Chinese Markdown notes that trace the author's data, assumptions, and conclusions.

[Read the example](#public-example) · [Install and run](#install-and-run)

![Cream-colored research pages, supply and demand charts, and copper annotations on a navy desk](docs/images/reportdecoder-hero.png)

[![CI](https://github.com/MakerFlyFly/ReportDecoder/actions/workflows/ci.yml/badge.svg)](https://github.com/MakerFlyFly/ReportDecoder/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Public example

In January 2013, the U.S. Energy Information Administration (EIA) forecast that global liquid fuels supply would grow by 1.0 million barrels per day that year. Its February 2014 report estimated growth at about 0.6 million barrels per day. The notes trace the gap to unplanned OPEC outages and explain how the report assessed risks to its 2014 and 2015 forecasts.

[English notes](samples/eia-2014-oil-supply/decode.en.md) · [Original PDF](samples/eia-2014-oil-supply/source.pdf) · [Chinese notes](samples/eia-2014-oil-supply/decode.zh-CN.md) · [Anonymized example in Chinese](samples/eia-2014-oil-supply/analysis.zh-CN.md)

## Output language and anonymization

- The note and chat overview normally follow the language of your request. An English request produces English notes even for a Chinese PDF. You can request either language explicitly. A bare attachment, path, or skill command defaults to Simplified Chinese.
- Regular decoding retains entity names, source attribution, page references, and figure numbers where they help explain the argument. Both languages support anonymization on request, with consistent aliases and identifying source details omitted.

Each request handles one text-based English or Chinese PDF. The skill reads charts and tables alongside the text, distinguishes estimates and forecasts from observed outcomes, and preserves units, date ranges, and conditions. Image-only scans need a text layer.

## Install and run

Bilingual output is available from `v0.3.0`. Download and extract the release ZIP or use this checkout, then copy the entire `research-report-reader` folder to a skill directory. [Download the latest release](https://github.com/MakerFlyFly/ReportDecoder/releases/latest)

- **Codex** uses `.agents/skills/` in the project or `~/.agents/skills/` in the home directory.
- **Claude Code** uses `.claude/skills/` in the project or `~/.claude/skills/` in the home directory.

Install Python 3.9 or later and the Poppler executables `pdfinfo`, `pdftotext`, and `pdftoppm`. For example, use `brew install poppler` on macOS or `sudo apt-get install poppler-utils` on Debian and Ubuntu. On Windows, put the Poppler executables on `PATH`. Check the installation from the repository root.

```bash
python research-report-reader/scripts/pdf_tools.py doctor
```

Reload the skill, then attach a PDF or provide its path. This request produces English notes.

```text
Use research-report-reader to decode this report and explain how the evidence supports its conclusions.
```

Request anonymization and a specific output language in the same prompt.

```text
Use research-report-reader to decode this report in English and anonymize the source and entities.
```

After upgrading from `v0.2.0`, English prompts produce English notes by default. To keep Simplified Chinese output in an English conversation, say `Decode this report in Simplified Chinese.` The finished note goes into `outputs` by default. The host model writes the note, and the PDF helper prepares the pages locally.

## Development and checks

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python -m unittest discover -s research-report-reader/tests -v
python scripts/package_skill.py --output-dir tmp/skill-build
```

CI checks PDF extraction and note creation, sample links, and the installable package on Ubuntu 22.04 with Python 3.9 and 3.12.

## License

The project's code, documentation, templates, and original notes use the MIT license. The sample PDF retains its publisher's terms and attribution. [MIT license](LICENSE) · [Third-party notices and source attribution](THIRD_PARTY_NOTICES.md)
