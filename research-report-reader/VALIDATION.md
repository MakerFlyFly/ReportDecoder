# 验收说明

## 自动检查

在仓库根目录运行：

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python research-report-reader/scripts/pdf_tools.py doctor
python -m unittest discover -s research-report-reader/tests -v
python scripts/package_skill.py
```

项目检查覆盖 skill 元数据、相对链接、公开 sample 的出处信息与 PDF 校验值。带 `--staged` 参数时还检查 Git 已暂存/跟踪文件是否处于公开目录，拒绝个人输出、临时目录和旧压缩包。

17 项 PDF 工具测试使用随包的虚构文件，覆盖按页提取、中文和特殊字符路径、空白页、图片页、密码保护、损坏输入、超时、局部失败、源文件变更和输出不覆盖。CI 先要求 `doctor` 通过，避免缺少 Poppler 时测试被跳过。

安装包使用明确文件清单，规范文本换行和归档时间；构建后检查内容、CRC、MIT 许可证和解压后的资源链接。它不会打包公开 sample 之外的原始材料，也不会打包工作目录的个人文件。

## 公开 sample 的内容核对

[公开 sample](https://github.com/MakerFlyFly/ReportDecoder/tree/main/samples/eia-2014-oil-supply) 为 2014 年 2 月的一份英文石油供给研究。原始 PDF 共 8 页，已完整提取文字并查看所有页面，3 幅图表均经视觉核对。

中文解读覆盖全球基准供给、上一年的预测偏差、产油国组织的剩余产能假设，以及利比亚、尼日利亚、伊朗、伊拉克、其他组织外产油国、美国陆上和海上、哈萨克斯坦新项目、北海检修等重要论点。

核对重点包括：

- 2013 年观察和估计，与 2014—2015 年预测分开表达；不补充后来发生的结果。
- 年平均、年底、季度和单月停产量分别保留；百万桶/日、千桶/日、桶/日与月度桶数不混用。
- 供给高于预测与供给低于预测的方向明确；不把供给上行误写成油价上涨。
- 对利比亚恢复、伊朗制裁、伊拉克扩容、美国钻井效率和项目延期的条件判断分别保留。
- 南苏丹中断量下降同时涉及生产恢复与有效产能下修，不能只保留其中一个原因。
- 匿名表达保持企业、机构、人物与直接识别项目的称谓一致；出处与使用说明单列于 sample README。

阅读质量通过逐段语义核对和连续通读检查，不按固定观点数、栏目数或逐字一致性评分。CI 不调用模型，也不能代替上述内容审阅。

## 环境与验证范围

PDF 工具和本次公开 sample 已在 Windows、Python 3.9 与原生 Poppler 环境执行。自动化流程配置为 Ubuntu 22.04 的 Python 3.9/3.12 矩阵，实际执行结果以仓库 CI 页面为准。

skill 的内容与目录结构可在 Codex 和 Claude Code 使用；当前端到端阅读在 Codex 中完成。没有据此声称 Claude Code 或 macOS 已完成实机验证。
