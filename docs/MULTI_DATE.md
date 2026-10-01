# Multi-date review / 多日期对比

Enter **2–12 distinct dates**, separated by commas. The program sorts them and keeps completed results tied to the submitted dates. Changing the date entry does not change old results. / 输入 2–12 个不同日期，以逗号分隔。程序自动排序；旧结果固定在运行时提交的日期，编辑输入后需重新运行。

## Quality records / 质量记录

![Four-date review / 四日期对比](screenshots/multi-date-en.png)

Choose the quality input folder in the main window, open **Multi-date review**, then **Compare dates**. The CSV tables are validated and imported once. All dates are calculated from that database. / 在主界面选择质量数据文件夹，打开多日期对比并运行。只验证与导入一次输入，所有日期使用同一数据库。

The chart shows open deviations and overdue actions. Tabs contain each date's totals, adjacent-date metric changes, deviation/action movements and newly available measurements. Double-click a row for its details. / 曲线展示未关闭偏差与逾期措施；表格显示各日期汇总、相邻变化、偏差与措施明细、新增检验。双击查看明细。

These are **endpoint comparisons**, not a reconstruction of edits or every short-lived overdue episode between dates. / 这是日期端点对比，不是编辑历史，也不涵盖两日期之间全部短暂逾期。

## Audit events / 审计事件

Load an audit log in **Audit log review**, then open its **Multi-date review**. It uses the captured review, so subsequent file edits do not alter that timeline. / 在审计窗口加载日志后打开多日期对比，使用已加载的复核结果，不受之后文件修改影响。

Counts use the event timestamp converted to **UTC end of day**. One event with several findings counts once under flagged events, but each finding counts separately. Missing/invalid timestamps appear in **Unknown dates**, never in dated totals. / 按事件时间转换至 UTC 日终计数。同一事件触发多条规则时，待复核事件仅计一次，检查项分别计数。无效时间戳单列，不进入日期总数。

The first period includes all dated events through the first date. Later periods use `(previous date, current date]`. Counts refer to the full-log rule review with its configured policy; they are **not** historical reviewer decisions, closure states or proven violations. / 首期含截至首日的全部有日期事件，后续采用“前一日期之后至当前日期（含）”。结果来自完整日志的规则复核，不代表历史复核结论、关闭状态或已证实违规。

## Export / 导出

Export is complete, independent of the displayed tab. It includes JSON, CSV tables, English/Chinese HTML reports and a final hash manifest. Quality runs also preserve the imported SQLite database. Choose a new output folder; partial folders without a completion manifest are not successful runs. / 导出包含全部结果，不只当前页：JSON、CSV、中英文 HTML 和最后写入的哈希清单。质量分析同时保留 SQLite。使用新目录；没有完成清单的目录不是成功结果。

Default synthetic quality example: open deviations **22 → 17**, overdue actions **30 → 33** from June 30 to July 31. No real-company result is claimed. / 默认模拟示例：6 月 30 日至 7 月 31 日，未关闭偏差 22→17，逾期措施 30→33；不代表真实企业结果。
