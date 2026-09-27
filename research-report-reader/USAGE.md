# 使用说明

## 文件包与环境

这是一个由宿主模型执行阅读和写作的 skill。PDF 脚本负责按页提取、渲染和分配匿名输出文件名，不会自行调用模型或生成研报结论。

当前写作规则为第 2 版：论证型内容按背景、研究重点、关键假设、依据与推导、结论组织，不适用的栏目省略；行情与指标跟踪用短段落或表格。首次用“某分析”引入，后续自然承接。完整性按原文内容核对，不要求固定观点数或每项都有五个栏目。

运行脚本需要 Python 3.9 或更高版本，以及 Poppler 的 `pdfinfo`、`pdftotext`、`pdftoppm`。脚本只使用 Python 标准库。所有工具需要位于 PATH；也可在子命令之后用 `--poppler-dir` 指定可执行文件目录。Windows 要指向含三个 `.exe` 的目录，而不是 `.cmd` 包装器目录。

在 macOS 通常可使用 `brew install poppler`，在 Debian/Ubuntu 通常可使用 `sudo apt-get install poppler-utils`。Windows 将已有 Poppler 的原生可执行文件目录加入 PATH。选择安装方式由使用者决定，skill 不自动安装软件。若系统只提供 `python3`，将示例中的 `python` 替换为 `python3`。

## 放置与调用

把整个 `research-report-reader` 文件夹复制到所选位置，保持内部结构不变。不要只复制 `SKILL.md`。

| 平台 | 当前项目使用 | 个人跨项目使用 | 显式调用 |
|---|---|---|---|
| Codex | `<项目>/.agents/skills/research-report-reader` | `~/.agents/skills/research-report-reader` | `$research-report-reader 阅读这份 PDF：<路径>` |
| Claude Code | `<项目>/.claude/skills/research-report-reader` | `~/.claude/skills/research-report-reader` | `/research-report-reader <路径>` |

Windows 中 `~` 通常指用户个人目录。Codex 也可按所在环境的现有个人 skill 目录放置；上表使用当前官方文档列出的发现路径。若未发现新 skill，重新加载 skills 或重启会话。

两端均可自然语言要求“使用这份 skill 阅读这份研报，结果保存到指定目录”。例如：

```text
使用 research-report-reader 阅读 D:\Reports\input.pdf，
保留精确数据和预测性质，输出到 D:\Notes\outputs。
```

输入一次一份文字版 PDF。无文字层扫描件不支持；密码保护且不可读取的文件需要先取得可正常打开的版本。文件包不自动安装到任何个人目录，不绑定 MCP、API 密钥、专属插件或某个型号的模型。

官方规则参考：[Codex skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code skills](https://code.claude.com/docs/en/skills)。这些是安装说明的链接，实际研报笔记不显示来源链接。

## PDF 脚本

在文件包根目录运行：

```text
python scripts/pdf_tools.py doctor
python scripts/pdf_tools.py extract "input.pdf"
python scripts/pdf_tools.py extract "input.pdf" --work-dir "private-work"
python scripts/pdf_tools.py render --manifest "<提取返回的manifest路径>" --pages "1,3-5"
python scripts/pdf_tools.py render --manifest "<manifest路径>" --pages all --dpi 72
python scripts/pdf_tools.py new-note --output-dir "outputs"
```

- `doctor` 检查三个原生程序能否运行。
- `extract` 每次新建独立目录，不覆盖历史结果。默认使用系统临时目录；`--work-dir` 改为在指定父目录下建立临时子目录。逐页保存 UTF-8 文字及 `manifest.json`，保留空页/失败页的位置。
- `render` 依据 manifest 读取原 PDF，先核对文件指纹。页码是从 1 开始的 PDF 物理页，仅内部使用。渲染输出采用新目录，不覆盖已有图片。DPI 范围为 72–300，默认 144。
- `new-note` 独占创建含“整理中”标记的匿名文件。模型按输出模板填充并核对后，才可标为完整。
- 子命令支持 `--help`。PDF 操作支持 `--timeout`，默认每次调用 60 秒；超时不会静默跳过。
- 输出为 JSON。原始工具诊断只保存在临时工作目录，错误摘要不回显 PDF 标题或输入文件名。

| 返回码 | 含义 | 后续行为 |
|---|---|---|
| 0 | 操作成功；提取时各页未触发自动复核标记 | 继续内容和图表核对，不能据此直接声称分析完整 |
| 2 | 输入、依赖、读取或操作失败 | 根据错误类型处理，不生成完整笔记 |
| 3 | 部分操作失败或文字质量需复核 | 检查 manifest 中的标记页及相应图像 |
| 4 | 所有页均没有可用的文字 | 检查文件类型，整篇扫描件不继续做 OCR |

提取质量标记采用保守启发式，不能证明材料是扫描件或已经充分阅读。图片图表可能不触发标记，应由模型结合全文和渲染页面检查。

临时文件含原始文字、诊断、文件路径和指纹。它们不应放入匿名笔记、共享压缩包或聊天附件。最终输出默认在调用工作区的 `outputs`，名称类似 `研报解读-20260101-120000-xxxxxxxx.md`，日期为处理时间，不是报告发布日期。

## 检查与测试

```text
python -m unittest discover -s tests -v
```

测试使用随包提供的虚构 PDF，运行真实 Poppler，覆盖中文与特殊字符路径、空白页、无文字层、加密、损坏、部分失败、渲染指纹及输出不覆盖。未安装 Poppler 的环境会跳过依赖它的测试并明确显示；跳过不等于通过。

`tests/fixtures/build_fixtures.py` 仅供开发者重建测试 PDF，需要额外的 `reportlab` 和 `pypdf`，日常使用和运行已有测试均不需要这两个库。业务验收说明见 `VALIDATION.md`。
