# BatchScope v0.7.0-alpha.3

The input check now highlights different ranges for the same product, test, method and unit. Open a finding to see its range, a different range and the related CSV row. Both records remain unchanged; check which specification version applies.

输入预检现在会提示同一产品、项目、方法和单位下的范围差异。打开问题能看到当前范围、对照范围和行号。两条记录均保留，适用的规格版本仍需核对。

Very small non-zero numbers such as `1e-999` are rejected instead of becoming zero. This applies to measurements, limits and laboratory edits. Invalid laboratory drafts also block exporting a previous result.

极小的非零数（如 `1e-999`）会报错，不再悄悄变成零。检验值、上下限和实验室修改都使用这一规则；实验室里的错误草稿也不能导出旧结果。

[Input check guide / 输入预检](INPUT_CHECK.md)

The Windows ZIP contains `BatchScope.exe`. Checksums and test records are attached to the release. Testing covers the build machine, not external user acceptance. The included data remains fictional.

Windows ZIP 内含 `BatchScope.exe`，发布附件包含校验值和测试记录。验证范围为构建机器，不是外部用户验收；自带数据仍是虚构示例。
