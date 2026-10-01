# Review notes / 复核记录

Select a finding in **Audit log review**, then **Add review note**. Enter your name, choose a status and record the reason. Click **Save review note**. / 在审计日志窗口选择一条检查项，点击填写复核记录，填写复核人、状态和理由，再保存。

| Status | Meaning / 含义 |
|---|---|
| Not reviewed / 未复核 | No decision recorded / 尚未填写处理记录 |
| In review / 正在复核 | Review is underway / 正在查证 |
| Retained for follow-up / 保留，需跟进 | More evidence or action is needed / 仍需证据或处理 |
| Explained; no follow-up / 已说明，排除跟进 | Reviewer records why no follow-up is needed / 记录无需继续跟进的理由 |

All original findings remain visible and exported. An explained finding still counts as a rule finding; changing status does not certify compliance or repair source data. / 原始检查项始终保留并导出。已说明的记录仍属于规则检查项，不代表合规认证，也不修复输入数据。

## Save and reopen / 保存与重新打开

Notes are stored separately in `outputs/review-notes/audit-notes.sqlite` when running from source, or `%LOCALAPPDATA%\BatchScope\outputs\review-notes\audit-notes.sqlite` in the Windows application. Reopen the same CSV with the same policy and rule version to retrieve them. / 备注单独保存在上述数据库；重新打开相同文件、使用相同规则配置和版本时会恢复。

Binding uses the source SHA-256, full policy and rule version. Renaming an unchanged file retains its notes; changing its bytes or policy starts a separate review context. Each finding is keyed by source row and rule, so repeated event IDs do not merge unrelated notes. / 绑定依据文件字节哈希、完整配置和规则版本。仅改名可恢复，内容或配置改变则分开。按源记录行号与规则关联，不因事件编号重复而合并。

Each save adds a revision. Two editors cannot silently overwrite one another: a stale editor must reopen the finding. Closing with unsaved edits offers save, discard or cancel. Filter by status or search note text to find follow-up work. / 每次保存新增一个版本；旧编辑窗口不能覆盖新记录，须重新打开。未保存关闭时可保存、放弃或取消。支持状态筛选与备注搜索。

## Export / 导出

Full exports contain the original findings plus `review-notes.json` (latest notes and history), `review_notes.csv` (latest notes), SQLite `review_notes` (all revisions), and notes in both HTML reports. Display filters do not limit exports. / 完整导出同时保留检查项、JSON 最新记录与历史、CSV 最新记录、SQLite 全部版本及中英文报告备注；不受当前筛选影响。

To join only the latest review to each finding / 只关联各检查项的最新复核记录：

```sql
WITH latest AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY source_row, rule ORDER BY revision DESC
  ) AS rn
  FROM review_notes
)
SELECT f.event_id, f.rule, n.status, n.reviewer, n.note
FROM findings f
LEFT JOIN latest n
  ON n.source_row = f.source_row AND n.rule = f.rule AND n.rn = 1;
```

Names are self-entered; local clock times and SQLite revision history are not authenticated identities, electronic signatures or tamper-proof audit trails. Back up the notes database before moving machines. / 复核人手动填写，本机时间与修改历史不是身份认证、电子签名或防篡改审计追踪。换机器前备份备注数据库。
