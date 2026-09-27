# 公开示例：全球石油供给预测中的不确定性

本例使用一份历史英文行业研究，展示 skill 如何识别预测、前提、依据及上下行风险，并生成中文匿名解读。

## 文件

- [原始报告 source.pdf](source.pdf)：官方下载文件，未修改。
- [中文解读 analysis.zh-CN.md](analysis.zh-CN.md)：由 ReportDecoder 的 AI 阅读流程生成并核对。
- [来源与校验元数据 source.json](source.json)。

## 来源与使用说明

**Source: U.S. Energy Information Administration (February 2014).**

原题：*Short-Term Energy Outlook Supplement: Uncertainties in the Short-Term Global Petroleum and Other Liquids Supply Forecast*。

- 发布机构：U.S. Energy Information Administration（EIA）。
- 发布日期：2014 年 2 月；获取日期：2026 年 9 月 27 日。
- 篇幅：8 页，包含 3 幅图表。
- [官方原始 PDF](https://www.eia.gov/outlooks/steo/special/pdf/2014_sp_01.pdf)。
- [EIA Copyrights and Reuse](https://www.eia.gov/about/copyrights_reuse.php)。

EIA 的使用政策说明其政府出版内容可使用和分发，并要求使用时注明来源与日期。本目录保留原始报告中的署名及说明；原始报告不重新许可为 MIT，涉及第三方材料和商标的权利仍归原权利人。

中文解读由 ReportDecoder 项目（MakerFlyFly 维护）的 AI 阅读流程编写和复核，不是 EIA 官方译文。解读对研究内容进行中文转述、重组与匿名化；出处集中记在本文件，解读正文不显示报告身份。所有预测均保持在原报告讨论的 2014—2015 年时点。

原始 PDF 的 SHA-256：

```text
af0858c0b212401518e4eefbb445647cfed59e4e56376544e6c9bcfa4530a758
```

## 复现

安装项目 skill 和 Python/Poppler 后，在仓库根目录向 Codex 或 Claude Code 发出：

```text
使用 research-report-reader 阅读 samples/eia-2014-oil-supply/source.pdf，
按 skill 生成完整的中文匿名精读笔记，保存到 outputs。
```

也可以先单独检查 PDF 处理：

```bash
python research-report-reader/scripts/pdf_tools.py doctor
python research-report-reader/scripts/pdf_tools.py extract samples/eia-2014-oil-supply/source.pdf
```

提取命令返回临时目录内的 `manifest`，据此调用 `render --manifest <路径> --pages all` 查看图表。`python scripts/validate_project.py` 会核对 PDF 校验值、文件和相对链接；它不会联网更新原文或重新调用模型。

生成文本可能随宿主模型变化。核对应关注基准预测、各地供给风险、成立条件、历史与预测期间，以及“百万桶/日”“千桶/日”“桶/日”的区别，不按段落数或逐字一致性评分。
