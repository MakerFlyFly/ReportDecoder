# ReportDecoder · 研报阅读 Skill

[![CI](https://github.com/MakerFlyFly/ReportDecoder/actions/workflows/ci.yml/badge.svg)](https://github.com/MakerFlyFly/ReportDecoder/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

输入一份文字版金融或经济研报 PDF，得到按论证关系组织的中文精读笔记。

ReportDecoder 先判断报告类型，再梳理研究重点、依据、推导和结论。论证段落保留必要背景与假设，行情和高频指标使用简短段落或表格。默认隐藏企业、人物、机构和来源身份，同时保留关键数值、期间、条件与不确定性。

**English:** A portable skill for Codex and Claude Code that turns financial and economic research PDFs into structured Chinese reading notes. It separates arguments from market observations, preserves data and forecast conditions, and anonymizes source identities. PDF preparation runs locally with Python and Poppler; reasoning and writing are performed by the host agent.

## 看一个完整示例

以 EIA 于 2014 年 2 月公开发布的全球石油供给预测研究为输入，演示背景、供给假设、预测偏差与地区风险的拆解：

- [示例说明与复现方法](samples/eia-2014-oil-supply/README.md)
- [官方原始 PDF](samples/eia-2014-oil-supply/source.pdf)
- [生成的中文匿名解读](samples/eia-2014-oil-supply/analysis.zh-CN.md)

示例原文保留历史预测时点。来源、署名及使用条款独立记录在示例说明中；它们不混入匿名解读正文。

## 能做什么

- 按宏观、行业、策略、公司、固收、量化、基金、衍生品、大宗商品等类别归类，允许并列类别。
- 通读文字与图表，合并重复表述，保留独立观点、重要子观点和风险条件。
- 区分事实观察、历史比较、模型测算、条件推演与实际验证。
- 用自然的中文表达；首次引入“某分析”，后续使用“该分析”或省略清楚的主语。
- 保留关键数值和统计口径，对影响理解的原文差异或计算缺口简短说明。
- 保存完整 Markdown，聊天中提供分类、导读和文件链接。

当前一次处理一份中英文文字版 PDF，输出为简体中文。整篇扫描件不在本版范围内。文字版 PDF 中的图片图表会按需渲染阅读。默认只还原输入报告，不联网更新数据，也不额外给出投资判断。

## 安装与调用

从 [Releases](https://github.com/MakerFlyFly/ReportDecoder/releases) 下载 skill ZIP 并解压，或克隆本仓库：

```bash
git clone https://github.com/MakerFlyFly/ReportDecoder.git
```

将完整的 `research-report-reader` 文件夹复制到相应目录，不要只复制入口文件。

| 平台 | 当前项目 | 个人跨项目 | 显式调用 |
|---|---|---|---|
| Codex | `.agents/skills/research-report-reader` | `~/.agents/skills/research-report-reader` | `$research-report-reader 阅读这份 PDF：<路径>` |
| Claude Code | `.claude/skills/research-report-reader` | `~/.claude/skills/research-report-reader` | `/research-report-reader <路径>` |

安装后让宿主重新加载 skill，必要时重启会话。两端共用同一套文件，不需要独立模型 API 密钥或 MCP 服务。读取和写作由宿主模型执行，Python 脚本本身不会调用模型。

### 运行依赖

- Python **3.9+**。
- Poppler 原生程序：`pdfinfo`、`pdftotext`、`pdftoppm`。
- 日常 PDF 脚本只使用 Python 标准库。

macOS 可通过 `brew install poppler` 安装，Ubuntu/Debian 可通过 `sudo apt-get install poppler-utils poppler-data` 安装。Windows 将已有 Poppler 原生 `.exe` 所在目录加入 PATH，或在脚本子命令后指定 `--poppler-dir`。如果系统使用 `python3`，将示例中的 `python` 替换为 `python3`。

在仓库根目录检查依赖：

```bash
python research-report-reader/scripts/pdf_tools.py doctor
```

详细命令、返回码和图表处理方法见 [使用说明](research-report-reader/USAGE.md)。

## 输入与输出

示例请求：

```text
使用 research-report-reader 阅读 samples/eia-2014-oil-supply/source.pdf，
生成完整的中文匿名精读笔记，输出到 outputs。
```

笔记包含分类、导读、主题目录和正文。解释原因或预测的内容按背景、研究重点、关键假设、依据与推导、结论组织，不适用的栏目省略。描述性数据使用段落或表格，不填充空栏目。

输出默认保存到调用工作区的 `outputs`，采用匿名文件名。个人报告、生成笔记和含身份的中间材料应留在本机；本仓库的公开 sample 有单独的来源与使用说明。

## 开发与验证

以下命令在仓库根目录运行：

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python research-report-reader/scripts/pdf_tools.py doctor
python -m unittest discover -s research-report-reader/tests -v
python scripts/package_skill.py
```

CI 在 Ubuntu 22.04 的 Python 3.9 和 3.12 环境运行上述检查。`doctor` 必须先通过，避免缺少 Poppler 时集成测试被跳过。现有测试覆盖中文与特殊字符路径、空白页、无文字层、密码保护、损坏输入、局部失败、原文件变更和输出不覆盖。

公开示例另经过全文、图表和数值核对。CI 检查文件、链接、元数据、原始 PDF 校验值和安装包；它不自动调用模型，也不将固定观点数或固定措辞视为阅读质量标准。具体范围见 [验收说明](research-report-reader/VALIDATION.md)。

安装包输出到 `dist`，只含 skill、使用说明、模板、脚本、虚构测试材料及许可证。原始 sample 和中文解读保留在 GitHub 仓库中。可从任意目录调用打包脚本，它不依赖本机 Codex 安装路径。

## 项目结构

```text
research-report-reader/   可独立安装的 skill、PDF 工具及测试
samples/                 公开报告、出处与使用说明、中文解读
scripts/                 项目检查与打包工具
.github/                 CI、问题反馈和 PR 模板
```

欢迎通过 [贡献说明](CONTRIBUTING.md) 提交改进或公开可用的案例。

## 许可证

项目原创代码、skill 文档、模板和原创解读采用 [MIT](LICENSE)。示例原文保留其自身权利状态和署名要求，不重新声明为 MIT；详见 [第三方材料说明](THIRD_PARTY_NOTICES.md)。
