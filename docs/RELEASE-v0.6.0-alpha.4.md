# BatchScope v0.6.0-alpha.4 — Audit import check / 审计日志导入检查

**English.** Download and extract the Windows ZIP, then run `BatchScope.exe`. The audit window now checks a selected CSV header before import and can inspect the format without changing the current review. Missing, unexpected or reordered columns are reported in the selected interface language. This is a read-only format check, not a LIMS adapter or data-integrity verdict. The desktop remains limited to 5 MB audit CSV files and an explicit UTC calendar. All 68 source tests passed; direct and ZIP-extracted executables passed 18 packaged checks. The executable is unsigned and has not been tested on an independent Windows computer.

**中文。** 下载并解压 Windows ZIP，运行 `BatchScope.exe`。审计日志窗口会在导入前检查 CSV 表头，也可单独只读检查格式而不覆盖当前复核；缺失、多余或顺序不符的字段按界面语言明确显示。这是格式检查，不是通用 LIMS 适配器，也不作数据完整性结论。桌面版仍限制 5 MB 审计 CSV，并使用明确的 UTC 日历。68 项源码测试通过；直接运行和 ZIP 解压后的 EXE 均通过 18 项打包自检。EXE 未签名，尚未在独立 Windows 电脑测试。
