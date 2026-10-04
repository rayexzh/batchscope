# BatchScope v0.6.0-alpha.5 — Truncated CSV checks / 截断 CSV 检查

**English.** Download and extract the Windows ZIP, then run `BatchScope.exe`. BatchScope now rejects audit logs and synthetic quality input CSVs whose quoted fields end without a closing quote. A malformed quality input is listed in `INPUT_ISSUES.csv`; no analysis database or completed report is produced. An audit import error leaves the previous review in place. These checks support review of the demo workflow; they do not validate a real GxP system. Source tests and packaged diagnostics are attached to the release. The EXE is unsigned and has not been tested on an independent Windows computer.

**中文。** 下载并解压 Windows ZIP，运行 `BatchScope.exe`。审计日志或模拟质量数据中的引号未闭合记录现在会被拒绝。质量输入错误写入 `INPUT_ISSUES.csv`，不会生成分析数据库或已完成报告；审计导入失败时保留上一份复核结果。这些检查只覆盖演示流程，不构成真实 GxP 系统验证。源码测试和打包自检记录见发布附件。EXE 未签名，尚未在独立 Windows 电脑测试。
