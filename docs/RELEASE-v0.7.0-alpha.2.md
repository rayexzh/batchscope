# BatchScope v0.7.0-alpha.2

Check the input folder before starting analysis. The new window lists missing files, incorrect values, blank measurements and possible duplicate entries. Double-click a finding to read it, or export the full report. Search filters the display only.

分析前可以先检查文件夹。新窗口列出缺失文件、错误数值、空白检验值和疑似重复；双击查看全文，也可以导出完整报告。搜索只影响显示。

Numeric fields no longer accept underscores, commas, formulas or unit text. The laboratory uses the same rule. The app does not fill blanks, remove repeats or convert units. Analysis records the hashes of the same bytes it used to build the database.

数值栏不再接受下划线、逗号、公式和单位文字，实验室也使用同一规则。程序不补空值、不删除复检、不换算单位；分析记录的文件校验值对应本次建立数据库所用的原始字节。

[Input check guide / 预检用法](INPUT_CHECK.md)

The Windows ZIP includes `BatchScope.exe`; Python is not required. Validation records and SHA-256 checksums are attached to the release. Checks were run on the build machine, not a separate clean VM or an external user's computer. This is still a synthetic-data learning tool.

Windows ZIP 内含 `BatchScope.exe`，无需安装 Python。验证记录及 SHA-256 校验值附在发布页面。测试在构建机器上进行，不是全新虚拟机或外部用户电脑验收；程序仍用于模拟数据学习。

109 source tests passed locally. The built and ZIP-extracted EXE passed native diagnostics, including checks before analysis and full exports. / 本地 109 项源码测试通过，构建后及 ZIP 解压后的 EXE 通过原生诊断，涵盖分析前预检与完整导出。
