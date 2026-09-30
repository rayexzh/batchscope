# Contributing to BatchScope / 参与批次质量洞察

BatchScope is an independent synthetic-data portfolio prototype. Useful contributions include reproducible bugs, corrections to metric definitions, and feedback on whether the review workflow is understandable.

BatchScope 是独立模拟数据作品集原型。欢迎可复现的问题、统计口径修正，以及对业务复核流程是否清晰的反馈。

## Report a problem / 报告问题

Open an issue with your Python/Windows version, the application version, steps to reproduce, the dates used, and expected versus actual behaviour. Use the supplied synthetic examples or a small fictional fixture. Screenshots can help explain interface problems.

提交 Issue 时说明 Python 与 Windows 版本、程序版本、操作步骤、分析日期、预期和实际结果。请使用自带模拟数据或小型虚构样例，界面问题可以附截图。

## Review the business case / 复核业务案例

Try [the worked case](docs/CASE_STUDY.md). Explain which record or definition was unclear, and what you expected to see. Identify feedback as a suggestion; the repository does not claim external validation unless documented with the reviewer's permission.

尝试[业务案例](docs/CASE_STUDY.md)，指出不清晰的记录或定义，以及你期望看到的内容。建议与正式验收需要分开记录；只有获得复核人员许可且有记录时，才可描述外部验证。

## Code changes / 代码贡献

Keep runtime dependencies in the Python standard library. Run `python -m unittest discover -v` from the project directory. Include a test when changing calculations, date scope or record identity. Update English and Chinese documentation for behaviour changes. Output directories and local databases are ignored by Git.

运行时保持 Python 标准库依赖。从项目目录执行上述测试命令。修改统计、日期范围或记录定位时提供相应测试；行为变化同步更新中英文说明。Git 不跟踪运行输出和本地数据库。

Do not submit patient, employee or confidential company records. / 不提交患者、员工或企业保密记录。
