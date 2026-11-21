# 公开示例：全球石油供给预测中的不确定性

同一份历史英文研报的两种中文读法，展示基准预测、依据、条件与供给风险。

## 文件

- [原始报告](source.pdf)
- [默认解码](decode.zh-CN.md)，保留 EIA、OPEC 等原名和用于核对结论的原文定位。
- [已有匿名解读](analysis.zh-CN.md)，展示按需隐去机构、企业与项目身份的写法。
- [来源与校验元数据](source.json)

## 来源与使用说明

**Source: U.S. Energy Information Administration (February 2014).**

原题：*Short-Term Energy Outlook Supplement: Uncertainties in the Short-Term Global Petroleum and Other Liquids Supply Forecast*。

- 发布机构：U.S. Energy Information Administration（EIA）。
- 发布日期：2014 年 2 月；获取日期：2026 年 9 月 27 日。
- 篇幅：8 页，包含 3 幅图表。
- [官方原始 PDF](https://www.eia.gov/outlooks/steo/special/pdf/2014_sp_01.pdf)。
- [EIA Copyrights and Reuse](https://www.eia.gov/about/copyrights_reuse.php)。

EIA 的使用政策说明其政府出版内容可使用和分发，并要求使用时注明来源与日期。本目录保留原始报告中的署名及说明；原始报告不重新许可为 MIT，涉及第三方材料和商标的权利仍归原权利人。

中文笔记由 ReportDecoder 生成并复核。默认解码按主题重组原文并保留来源，匿名解读的出处集中记在本文件。两份笔记都把 2014—2015 年的数据表述为报告当时的预测。

原始 PDF 的 SHA-256：

```text
af0858c0b212401518e4eefbb445647cfed59e4e56376544e6c9bcfa4530a758
```

## 复现

安装项目 skill 和 Python/Poppler 后，在仓库根目录向 Codex 或 Claude Code 发出：

```text
使用 research-report-reader 阅读 samples/eia-2014-oil-supply/source.pdf，
按论证关系生成中文精读笔记，保存到 outputs。
```

需要匿名时，在请求中加上“请匿名解读”。

也可以先单独检查 PDF 处理：

```bash
python research-report-reader/scripts/pdf_tools.py doctor
python research-report-reader/scripts/pdf_tools.py extract samples/eia-2014-oil-supply/source.pdf
```

提取命令返回临时目录内的 `manifest`，据此调用 `render --manifest <路径> --pages all` 查看图表。`python scripts/validate_project.py` 会核对 PDF 校验值、文件和相对链接；它不会联网更新原文或重新调用模型。

生成文本可能随宿主模型变化。核对应关注基准预测、各地供给风险、成立条件、历史与预测期间，以及“百万桶/日”“千桶/日”“桶/日”的区别，不按段落数或逐字一致性评分。
