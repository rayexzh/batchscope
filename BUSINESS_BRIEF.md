# Business brief / 业务解释

## Problem / 问题

Separate batch, laboratory, deviation and action files make it easy to lose context or confuse current status with status at a historical date. A low closed-case average alone can conceal a large unresolved backlog. Missing measurements can also distort rates if they are counted as zero.

批次、检验、偏差和措施分散在不同表里，容易丢失关联或混淆历史状态。只看已关闭偏差的平均时长，可能忽略未关闭的积压；把缺失检验值当零，也会误算比例。

## Decision supported / 支持的决定

This prototype helps a reviewer choose records to inspect. It joins four related tables and makes the date and denominators explicit. It does not automatically conclude that a batch is defective, approve release, evaluate an employee or establish CAPA effectiveness.

这个原型帮助复核人员选择需要查看的记录。它连接四张表，明确分析日期和分母，不能自动认定批次有缺陷、批准放行、评价员工或判断 CAPA 有效。

## Example interpretation / 示例解释

The fixed-seed June 30 demo contains 198 measurements in scope, of which 184 are judgeable, 14 are missing and 74 are outside fictional ranges. A reviewer should inspect the product/test/method/unit/bounds groups and missing values before interpreting the flags. The intentionally artificial frequency is not an industry benchmark.

示例中截至 6 月 30 日的 198 条检验记录，有 184 条可判定、14 条缺失、74 条超出虚构范围。应先查看具体产品、项目、方法、单位、上下限的分组和缺失情况。这是人为模拟的频率，不是行业基准。

There are 22 deviations still open and 30 outstanding overdue actions. The age and due-date lists show where to begin a review; they do not establish severity, root cause or the right corrective action. A closure occurring in July remains open in the June view.

还有 22 条未关闭偏差、30 条未完成且逾期的措施。列表帮助确定从哪里开始复核，不直接说明严重程度、根本原因或正确的纠正措施。7 月才关闭的偏差在 6 月视图仍未关闭。

## Evidence and learning / 证据与学习

The source, data dictionary, relational schema, three SQL queries, reproducible inputs and known expected tests are available locally. A short demonstration should explain one JOIN, why future completions are excluded, and why NULL measurements are not zero. Record external feedback separately; no employer adoption is currently claimed.

展示时讲清楚一条 JOIN、为什么不能提前使用未来的完成状态，以及为什么 NULL 不能等于零。外部反馈需要单独记录，目前不能声称已经被药企采用。
