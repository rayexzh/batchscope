# v0.7.0-alpha.4 修复记录 / Fixes

| 操作 / Task | 修复后 / Result |
|---|---|
| 切换检验记录 / Switch tests | 保留各条记录的草稿。 / Keep drafts for each record. |
| 修改复检计划 / Edit a repeat plan | 重新评价后才能导出；关闭会提醒未处理的草稿。 / Require re-evaluation before export; warn before discarding drafts. |
| 关联编号填错 / Enter an unknown ID | 显示真实列名、填入的编号和目标表。 / Show the column, entered ID and target table. |
| 缩小审计窗口 / Resize the audit window | 按钮换行，记录和说明可滚动查看。 / Wrap buttons and scroll to records and notes. |

使用模拟数据自动测试，126 项通过；原始数据未改动。 / 126 automated tests passed with fictional data; source data stayed unchanged.

草稿只保留在打开的窗口内。高精度小数仍受浮点舍入影响，见[输入说明](INPUT_CHECK.md)。 / Drafts last only while the window is open. Decimal precision remains limited by floating-point rounding; see the [input guide](INPUT_CHECK.md).

[测试记录 / Test results](validation/qc-workflow-20261016.json) · [回归测试 / Regression tests](../test_qc_workflow_ui.py) · [按钮截图 / Buttons](screenshots/audit-small-controls-en.png) · [记录截图 / Records](screenshots/audit-small-evidence-en.png)
