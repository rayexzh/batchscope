# Audit log review / 审计日志复核

This first module reviews **synthetic audit events**. It does not connect to a LIMS or reconstruct a system's true audit trail. / 第一版复核模拟操作日志，不连接 LIMS，也不重建真实系统审计追踪。

## Start / 开始

Run `python app.py`, open **Audit log review / 审计日志复核**, then **Generate sample log / 生成模拟日志**. The six-event example gives six findings affecting four events. Search by user, event, rule or batch; double-click a finding for the original operation and policy. Export always includes the full result, regardless of search. / 运行源码后打开入口，生成示例。6 条事件产生 6 个检查项，影响 4 条事件。搜索后双击查看原始操作；导出始终包含完整结果。

If a quality analysis exists when you open the audit window, sample batch IDs come from that snapshot. **Open linked batch** uses that captured snapshot, even if the main window later runs another analysis. Demonstration test/deviation IDs are fictional and are not matched to actual test records. / 已有质量分析时，示例批次来自该快照；关联查看固定使用窗口打开时的快照。示例检验与偏差编号为虚构值，不声称匹配真实检验记录。

## Format / 格式

CSV columns, in order / CSV 列及顺序：

```text
event_id,timestamp,user_id,role,action,record_type,record_id,batch_id,old_value,new_value,reason
```

Timestamp: ISO 8601 with offset, e.g. `2026-06-29T10:00:00+00:00`. Original cells are retained. Identity fields cannot be blank; a batch link may be absent. Supported actions: `create`, `update`, `delete`, `access_change`. / 时间戳须含时区，保留原始单元格。身份字段不能为空，批次关联可为空。

## Rules / 规则

| Rule | Meaning / 含义 |
|---|---|
| `reason.missing` | Update/delete/access change with blank reason / 修改、删除或权限变更未填原因 |
| `permission.mismatch` | Action outside configured role permissions / 操作不在配置角色权限内 |
| `permission.unknown` | Unknown role/action: policy coverage gap, not proven unauthorised action / 角色或操作未覆盖，不证明越权 |
| `timestamp.invalid` | Invalid or timezone-free timestamp / 无效时间戳或无时区 |
| `timestamp.order` | A timestamp precedes an earlier supplied event for the same record / 同记录时间按输入顺序倒退 |
| `time.outside_hours` | Mutation outside the configured working calendar; context only / 工作时间外修改，仅提供上下文 |
| `event.duplicate` | Event ID repeats; findings still link by source record number / 事件编号重复，仍按源记录序号关联 |
| `event.incomplete` | Required identity field blank / 必需标识字段为空 |

Default demonstration policy: **UTC, Monday–Friday, 08:00 inclusive–18:00 exclusive**. QC: create/update; QA: create/update/delete; admin: access_change. These are fictional permissions, not pharmaceutical regulations. No role is presumed authorised merely because it is named admin. / 默认日历为 UTC 周一至周五 08:00（含）至 18:00（不含）。权限为示例，不是法规，也不因账号叫管理员就认为其被授权。

Choose a policy JSON to change work hours, working days and permitted operations. Only UTC calendars are supported in this iteration, avoiding unhandled daylight-saving assumptions. Overnight shifts require a future calendar implementation. / 可选择 JSON 修改工作时间、工作日与权限；本版只支持 UTC，不支持跨午夜班次及地区夏令时日历。

CLI / 命令行：

```powershell
python audit_trail.py path/to/audit_events.csv --output outputs/audit-first
# Optional / 可选： --policy path/to/policy.json
```

Use a new output folder. Export includes SQLite events/findings with row-based joins, CSV findings, full JSON evidence, English/Chinese HTML reports, source SHA-256, rule version and applied policy. The source CSV is never modified. / 使用新输出目录；导出含 SQLite 原始事件与检查项、CSV、JSON、中英文 HTML、源文件哈希及规则配置，不修改输入文件。

## Limits / 边界

Example evidence query in `audit.sqlite` / 在数据库中查看操作与检查项的关联：

```sql
SELECT e.event_id, e.timestamp, e.user_id, e.role, e.action,
       e.old_value, e.new_value, e.reason, f.rule, f.level
FROM findings f
JOIN events e ON e.source_row = f.source_row
ORDER BY e.source_row, f.rule;
```

The join uses source row identity rather than event ID, so repeated event IDs do not duplicate the evidence join. `manifest.json` is written last; a folder without it is an incomplete export. / 按源记录行号关联，避免重复事件编号造成重复关联。最后写入 `manifest.json`；缺少该文件的目录属于未完成导出。

Input rows are not a trusted sequence. A time-order flag can reflect sorting/export issues. Role labels do not establish historical authorisation; production use would need permissions effective at event time. Hashes identify bytes, not authenticity or tamper-proof storage. No digital signatures, inspection verdict, ALCOA+ certification or Part 11 compliance claim is made. / 输入行不是可信序列，倒序可能来自导出排序；角色标签不能证明操作时授权。哈希不证明真实性或防篡改。本模块不提供电子签名、检查结论或合规认证。

Desktop input is capped at 5 MB and processed locally in memory. The module is included in v0.6.0-alpha.1; earlier EXEs do not include it. / 桌面输入上限 5 MB，本地内存处理。v0.6.0-alpha.1 已包含本模块，旧 EXE 不包含。

Open **Multi-date review** to compare events across dates. See the [counting rules](MULTI_DATE.md). / 打开多日期对比查看各日期事件统计，口径见[多日期说明](MULTI_DATE.md)。
