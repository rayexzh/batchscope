# Worked case: month-end quality review / 业务案例：月末质量复核

**Fictional data, not an employer result. / 虚构数据，不是企业实际成效。**

Question: What changed from 30 June to 31 July 2026, and which records should a reviewer inspect? / 问题：2026 年 6 月底到 7 月底发生了什么，复核人员应查看哪些记录？

Source: the supplied `examples/synthetic-v1` (100 batches, 200 measurements, 33 deviations, 66 actions). Both endpoints use one input snapshot. / 来源：项目自带模拟数据，两端使用同一份输入快照。

| Metric / 指标 | June / 六月 | July / 七月 | Change / 变化 |
|---|---:|---:|---:|
| Measurements / 检验记录 | 198 | 200 | +2 |
| Judgeable / 可判定 | 184 | 186 | +2 |
| Missing / 缺失 | 14 | 14 | 0 |
| Outside example range / 超示例范围 | 74 | 75 | +1 |
| Open deviations / 未关闭偏差 | 22 | 17 | −5 |
| Overdue actions / 逾期措施 | 30 | 33 | +3 |

## Interpretation / 解读

Five deviations that were open in June closed by July; 17 remained open. The supplied dates explain the backlog decline. This alone does not establish CAPA effectiveness or a faster process. / 六月底积压的 5 条偏差已关闭，17 条仍未关闭。给定日期可以解释积压减少，但不足以证明 CAPA 有效或流程提速。

Four actions entered the ending overdue list and one previously overdue action completed; 29 remained overdue. The net increase of three hides both inflow and completion. A reviewer can search the action IDs, inspect their dates and confirm the recorded status. Lateness is not a quality-risk score. / 4 条措施新进入期末逾期列表，1 条期初逾期措施完成，29 条持续逾期。净增加 3 条包含了新增和完成两类变化。复核人员可以定位措施编号、查看日期并确认状态，逾期天数不等于质量风险评分。

Two additional measurements entered scope; one was outside its fictional range. Existing missing values remain missing. Counts alone do not establish declining manufacturing quality; inspect method, unit, bounds and the appropriate denominator. / 2 条检验新进入范围，其中 1 条超出虚构示例范围。原缺失值仍为缺失。计数不足以判断生产质量下降，应检查方法、单位、范围与分母。

## Reproduce / 复现

Run from the project folder, using a new output directory: / 从项目目录运行，输出目录必须尚不存在：

```powershell
python comparison.py examples/synthetic-v1 outputs/case-month-end --from 2026-06-30 --to 2026-07-31
```

Inspect `COMPARISON.md`, the movement CSVs and `manifest.json`. SQL and record-level outputs support explaining each change; they do not prove its operational cause. / 查看摘要、变化 CSV 与完成清单。SQL 和记录明细帮助解释变化构成，但不证明其业务原因。

Portfolio value: demonstrate related-table modelling, reproducible as-of queries, input checks, NULL handling, stock reconciliation and a desktop review workflow. Seek feedback on whether a domain reviewer can answer the question without assistance. / 作品集价值：展示关联表建模、可复现历史日期查询、输入检查、缺失值处理、存量对账与桌面复核流程。下一步请业务人员试用，确认其能否独立回答上述问题。
