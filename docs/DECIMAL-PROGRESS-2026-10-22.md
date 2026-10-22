# Decimal values and saved progress / 小数与进度保存

- Results and limits are compared without rounding. Their input text is retained in CSV, JSON and SQLite. JSON measurements now use strings.
- Save progress stores the baseline snapshot, staged changes, unfinished forms and repeat plans in a new `.bslab` file. Open it from the main window, then run the comparison again before exporting.
- Existing saved progress is not overwritten. Give each saved copy a new name.

- 检验值和上下限不先舍入，CSV、JSON 和 SQLite 保留输入文本。JSON 中的检验数值改为字符串。
- 「保存进度」把基准数据、排队修改、草稿和复检计划保存到新的 `.bslab` 文件。主窗口可打开；重新计算后再导出。
- 已有进度不会覆盖，每次另取文件名。

Local checks: 129 automated tests passed on Windows / Python 3.14, including native Tk controls. Checks cover decimal boundaries, replayed exports, progress restored without its original output folder, altered snapshot rejection, and pending drafts blocking export. These are synthetic checks, not a human QC trial or GxP validation.

本地 129 项自动检查通过，环境为 Windows / Python 3.14，包含原生 Tk 控件。覆盖临界小数、导出重算、原输出目录删除后的恢复、快照被改时拒绝加载、草稿阻止导出。这是模拟检查，不是真人 QC 试用或 GxP 验证。

[Laboratory instructions / 实验室说明](LABORATORY.md)
