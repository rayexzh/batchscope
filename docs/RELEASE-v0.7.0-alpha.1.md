# BatchScope v0.7.0-alpha.1

The quality data laboratory lets you try changes to synthetic measurements, bounds and dates. Compare baseline and scenario counts at one as-of date, inspect each edited record, reset the exercise, and export both inputs for replay.

新增质量数据实验室：修改模拟检验值、范围和日期，在同一截至日期比较原始与假设情景，查看逐条修改，恢复原始状态，导出两份可重跑输入。

Two- and three-attempt practice retains the original result and every later attempt. Narrowing a teaching range does not establish accuracy; no average, final-pass score, OOS conclusion or release decision is produced.

二次、三次检验练习保留首次及后续每轮结果。收窄练习范围不证明准确性；不生成平均后合格、最终通过分数、OOS 结论或放行判断。

[Usage and boundaries / 使用方法与范围](LABORATORY.md)

The laboratory uses the existing SQL rules on an isolated captured snapshot. Source CSVs, the completed database and main-window results stay unchanged. Scenario and repeat-exercise exports can be replayed and include a completion manifest.

实验室在独立快照上复用原有 SQL 规则；源 CSV、已完成数据库及主界面结果不变。情景及重复练习导出保留完整记录与完成清单。

95 source tests passed locally and in [GitHub Actions for the feature commit](https://github.com/rayexzh/batchscope/actions/runs/38762261823). The built and ZIP-extracted EXE passed native diagnostics including the laboratory, three retained attempts, reset and export. Testing used the build machine, not an independent clean VM or external user acceptance. The release includes checksums and validation JSON.

95 项源码测试在本地及上述 GitHub Actions 通过；EXE 在构建后及 ZIP 解压后，完成实验室、三轮记录保留、恢复与导出诊断。验证范围为构建机器，不是独立全新虚拟机或外部用户验收。发布附件包含校验值及验证 JSON。
