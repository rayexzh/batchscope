# Data dictionary / 数据字典

All inputs are synthetic. CSV headers must match the listed names and order; encoding is UTF-8 (BOM accepted). Dates use YYYY-MM-DD. Blank optional fields become NULL. Mandatory text is trimmed and must not be empty. Every table has a unique, non-empty first-column ID.

| Table | Field(s) | Meaning and validation / 含义与校验 |
|---|---|---|
| batches | batch_id | Primary key / 批次主键 |
| batches | product | Fictional product name, not an actual medicine / 虚构产品 |
| batches | manufactured_on | Manufacture date / 生产日期 |
| test_results | test_id, batch_id | Measurement primary key, batch foreign key / 检验编号与批次外键 |
| test_results | test_type, method | Example measurement and method names / 示例项目与方法 |
| test_results | value | Finite numeric value; blank allowed, never imputed as zero / 可为空，非零填充 |
| test_results | unit, spec_unit | Result and bound units must match exactly; no automatic conversion / 单位须一致 |
| test_results | spec_low, spec_high | Mandatory finite fictional limits, low <= high / 虚构上下限 |
| test_results | measured_on | Measurement date, on/after manufacture / 检验日期不早于生产 |
| deviations | deviation_id, batch_id | Deviation primary key and batch foreign key / 偏差编号与批次外键 |
| deviations | category | Example category; not a risk classification / 示例分类，非风险分级 |
| deviations | opened_on, closed_on | Opening date; optional closure, not earlier than opening / 关闭日期可为空且不早于开启 |
| actions | action_id, deviation_id | Action primary key and deviation foreign key / 措施编号与偏差外键 |
| actions | owner_role | Fictional role, no real employee identity / 虚构负责人角色 |
| actions | created_on | Creation date, on/after deviation opening / 不早于偏差开启 |
| actions | due_on | Mandatory due date, on/after creation / 约定日期不早于创建 |
| actions | completed_on | Optional completion, not earlier than creation / 完成日期可为空 |

Source metadata: `SOURCE.json` must be a JSON object with `data_type: synthetic`. The supplied generator also records its version, seed, batch count and fixed date origin. All four CSVs and this metadata file receive input SHA-256 hashes in the analysis manifest.

## Metric definitions / 指标定义

- `outside_range_pct`: 100 × outside-range records ÷ judgeable records, separately for each product/test/method/unit/bounds group. No judgeable records means NULL, not 0%.
- `oldest_open_days`: maximum calendar-day age of deviations still open at the as-of date. NULL if the group has no open deviations.
- `mean_closed_duration_days`: mean closure duration only for records closed on/before the as-of date; interpret beside the open backlog, never as a standalone performance score.
- `overdue_actions`: outstanding actions with due date earlier than the as-of date. Completed after that date remain outstanding at that date. Actions due that day are not overdue.

This model is an educational snapshot, not a complete event-sourced quality management system. It has no specification version history, re-opening history or proof of actual investigation outcomes.

## Record details / 记录明细

Three `*_details.csv` files use exactly the same date scope as their summary queries. Measurement groups use product, test, method, unit and both bounds; deviation groups use product and category; action rows match the selected action ID.

- `snapshot_status`: measurement `missing`, `outside_range`, or `within_range`; deviation `open` or `closed`; action `overdue`. These are snapshot review labels, not investigation conclusions.
- `closed_on_source`, `completed_on_source`: the dates recorded in the source, which may be later than the as-of date. They do not override snapshot status.
- `open_age_days`: age at the as-of date for still-open deviations; NULL for deviations already closed by then.
- `closed_duration_days`: opening-to-closure duration for deviations closed by the snapshot; NULL while still open at that date.

明细保存编号、批次和日期以便复核；缺失检验值仍为 NULL。界面搜索或筛选只影响显示，不改动汇总、原始输入或完整导出。
