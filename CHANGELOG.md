# Change log / 更新日志

## v0.7.0-alpha.1 (2026-10-15) — Quality data laboratory / 质量数据实验室

- Add an isolated quality data laboratory for synthetic result, bound and date changes, with same-date comparisons, reset and replayable exports. / 新增独立质量数据实验室，支持模拟检验值、范围、日期修改，同日对比、恢复与可重跑导出。
- Add two-/three-attempt teaching exercises. Keep all results and the initial outside-range flag; never average results into a release decision. / 新增二次、三次检验练习，保留全部结果及初始超范围提示，不通过平均结果生成放行结论。

- Ignore surrounding whitespace when comparing event and record identities; preserve original imported values. Blank identifiers are flagged as incomplete and do not link unrelated events. / 比较事件与记录标识时忽略首尾空格，原值仍保留；空白标识提示不完整，不关联无关事件。
- Reject header-only audit logs without replacing a previous desktop review. / 拒绝只有表头的空审计日志，保留上一份桌面复核结果。
- Audit ruleset is now `audit-review-0.2`. Notes remain bound to their original ruleset and are not silently transferred to a changed review. / 审计规则集更新为 `audit-review-0.2`；旧备注仍绑定旧规则，不自动转移到新结果。
- Windows package includes these changes; 95 source tests and built/extracted EXE diagnostics passed. / Windows 包包含以上修改；95 项源码测试及构建后、解压后 EXE 诊断通过。

## v0.6.0-alpha.5 (2026-10-04) — Reject truncated CSV / 拒绝截断 CSV

- Reject quoted fields cut off at end of audit logs or quality input files. / 审计日志与质量输入文件中的引号未闭合记录不再被误读。
- Quality inputs now produce an `INPUT_ISSUES.csv` entry and stop before creating analysis outputs; audit import preserves the prior review on error. / 质量输入错误写入问题清单并阻止分析输出；审计导入出错时保留上一份复核。
- Added regressions for both workflows. Simulated QA/QC review is not regulatory validation or external user feedback. / 两条流程均有回归测试；模拟岗位试用不等于法规验证或外部用户反馈。

## v0.6.0-alpha.4 (2026-10-04) — Audit CSV import check / 审计日志导入检查

- Check a log CSV's header before import and show missing, extra or reordered fields. / 导入前检查表头，明确提示缺失、多余或顺序不符的字段。
- Offer a read-only format check without changing the current review. / 增加只读格式检查，不覆盖当前复核结果。
- Preserve the documented 5 MB desktop limit and UTC-only policy; this is not a general LIMS adapter. / 保留桌面版 5 MB 和 UTC 限制；不声称兼容所有 LIMS。

## v0.6.0-alpha.3 (2026-10-04) — Review-note layout / 复核记录窗口

- Make the note form scrollable at its minimum size and keep the save action visible. / 最小窗口下可滚动查看修改历史，保存按钮保持可见。
- Add a geometry regression and packaged check; 67 source tests pass. / 新增界面及 EXE 检查；67 项源码测试通过。
- Document task-based AI role walkthroughs separately from real user feedback. The existing animation remains labelled v0.6.0-alpha.1. / 单独记录模拟岗位试用，不冒充真人反馈；原动画保留原版本标识。

## v0.6.0-alpha.2 (2026-10-01) — Review notes / 复核记录

- Add four review statuses, reviewer-entered reasons, status filtering and note search. / 新增四种复核状态、处理理由、状态筛选与备注搜索。
- Keep local revisions separate from source logs; bind notes to source bytes, policy and ruleset. Reject stale-editor saves. / 本地历史与原日志分开，绑定文件、配置和规则版本，拒绝旧窗口覆盖。
- Include latest notes and revision history in complete exports. Prompt before closing unsaved edits. / 完整导出附备注与历史，未保存关闭时提示。
- Six new tests, 66 total. The previous 78-second video remains labelled v0.6.0-alpha.1. / 新增六项测试，共 66 项；旧视频保留其版本标识。

## v0.6.0-alpha.1 (2026-10-01) — Audit logs and multiple dates / 审计日志与多日期对比

- Add synthetic audit logs, explicit role permissions and a UTC working calendar. / 新增模拟日志、明确的角色权限及 UTC 工作日历。
- Review missing reasons, permission mismatches, unknown policy coverage and timestamp anomalies; flags are review prompts. / 复核原因缺失、权限不匹配、规则覆盖缺口及时间异常，不作违规结论。
- Add desktop search, source evidence, fixed-snapshot batch links and full SQLite/CSV/JSON/bilingual HTML exports. / 新增桌面搜索、原始操作、固定快照批次关联和完整导出。
- Compare 2–12 quality snapshots and adjacent-date movements; count audit events by UTC date and keep invalid timestamps separate. / 对比 2–12 个质量快照及相邻变化；审计事件按 UTC 日期统计，无效时间戳单列。
- Add a 78-second illustrated explainer with bilingual chapter text and synthetic English narration. / 新增 78 秒动画讲解，含中英文字与合成英文旁白。
- 13 new tests; 60 local tests pass. Rebuilt Windows EXE includes both new modules. / 新增 13 项测试，本地共 60 项通过；新版 EXE 包含两个新模块。

## v0.5.0-alpha.4 (2026-10-01) — Snapshot input clarity / 快照输入与窄窗口

- Wrap date actions when the window cannot fit their full labels. / 日期操作在空间不足时换行。
- Keep completed snapshots and show their input folder; changed inputs/dates display a pending-analysis notice. / 旧快照注明输入，新输入或日期提示尚未分析。
- 47 local source tests passed; packaged diagnostics include changed-input and date-layout regressions. / 本地 47 项测试通过，EXE 自检同步覆盖。
- Based on AI-scripted native desktop review, not real teacher feedback or external adoption. / 来自模拟界面试用，不声称真实教师认可。

## v0.5.0-alpha.3 (2026-10-01) — Clear review recovery / 复核恢复与导航

- Validate calendar and date order before clearing results or reserving output. Bad dates keep the last completed snapshot. / 无效日期提前校验，保留原成功快照。
- Hide the action filter on full-snapshot age/month tabs; preserve its choice when returning. / 措施筛选只在措施跟进显示。
- Add standalone quick-start and navigation; historical alpha.2 demo and simulated teacher review remain labelled. / 独立启动导航并标注旧演示版本。
- Validation: 45 local source tests passed; packaged EXE evidence is supplied with the release. / 本地 45 项测试通过，EXE 证据见附件。

## v0.5.0-alpha.2 — Portable self-test path fix / 便携版自检路径修复

- Resolved relative self-test folders before constructing an isolated user-output profile. The first tagged EXE CI run exposed a false path-reconciliation failure when using the documented relative command. / 将自检目录先解析为绝对路径；首次标签构建发现相对路径命令造成输出位置核对误报，已复现并修复。
- Print packaged-test diagnostics and retain build artifacts even if a CI step fails. Keep alpha.1 and its tag as release history. / 云端自检失败时打印诊断并保留构建产物，保留 alpha.1 及标签历史。

## v0.5.0-alpha.1 — Quality follow-up and Windows EXE / 质量跟进与 EXE

- Added a quality review workbench: outstanding action timing, closed-parent follow-up, open deviation age bands and reconciled monthly backlog movements. Time urgency is not quality-risk ranking. / 新增措施跟进、已关闭偏差关联措施提醒、积压分段与月度对账；时间紧迫度不是质量风险。
- Added fixed-date batch overviews linking measurements, deviations and all visible actions, plus a bilingual offline HTML review report and three additional hashed CSVs. / 新增批次全景、双语离线复核报告与三个 CSV 导出。
- Separated bundled read-only SQL resources from persistent EXE output in the user profile. Added an isolated PyInstaller build, portable ZIP, checksums, EXE self-test and Windows build workflow. / 内置 SQL 与用户输出分离，增加隔离打包、便携 ZIP、哈希、EXE 自检与构建工作流。
- Moved review controls to a separate row and provided scrollable review/batch layouts for larger fonts. / 复核操作独立排列，工作台和批次窗口支持大字体滚动。
- Validation: 43 source tests; packaged-EXE and release-download results are supplied with release evidence. / 源码 43 项测试，打包与下载后验证结果随版本提供。

## v0.4.0-alpha.1 — Two-date review / 两日期复核

- Named the independent project **BatchScope / 批次质量洞察**, with consistent desktop, report and bilingual documentation names. Maintained separately from RxDataLint. / 统一独立项目名称、界面、报告与双语介绍，和 RxDataLint 分开维护。

- Added a two-date comparison using one validated SQLite input snapshot, with six metric deltas and record-level deviation, overdue-action and new-measurement movements. / 使用同一份已校验输入快照，新增六个指标净变化与三类记录变化。
- Added a separate desktop comparison view with search, continuing-record visibility, sorting, copying and synchronized language/theme. Dates and data stay fixed after later main-window edits. Scrollable layout supports larger fonts. / 新增独立对比窗口，支持搜索、持续记录显示、排序、复制、语言主题同步及大字体滚动；旧窗口保持快照。
- Added four comparison CSV exports, start/end snapshots, a bilingual summary and a parent manifest covering nested artifacts. Added a worked synthetic business case. / 增加四个对比 CSV、两端快照、双语摘要、嵌套文件哈希清单与模拟业务案例。
- Explicitly distinguish net stock changes from interval activity; opened-and-closed deviations are separate, and completed overdue episodes absent at both endpoints are not counted as endpoint movements. / 明确存量变化与期间活动的区别，避免误解新增逾期口径。
- Validation: 33 local tests passed, including movements, dates, source stability, hashes and background failure/recovery. Local comparison screenshots checked in Chinese/English and large-font mode. / 本地 33 项测试通过，已检查双语与大字体对比截图。

## v0.3.0-alpha.1 — Desktop presentation / 桌面界面

- Added Chinese/English UI switching, light/dark palettes, adjustable native fonts and Windows DPI-awareness setup. Open detail windows keep snapshot data and filters while changing presentation. / 新增语言与主题切换、字体大小调整和 Windows DPI 适配，明细保留快照与筛选。
- Added row context menus, clipboard copying with headers, identifier copying and numeric/text sorting with NULL values last. Stable row IDs preserve the clicked/selected record. / 新增右键菜单、复制与排序，保持记录定位正确。
- Moved range flags and rates ahead of secondary columns, added six metric cards, alternating rows, responsive wrapping and page scrolling. Activity bars hide when processing ends. / 关键指标前移，增加指标卡片、隔行底色、自动换行与页面滚动，完成后隐藏进度条。
- Validation: 24 local tests passed. Local native-window screenshots were inspected in Chinese/English, light/dark and large-font modes. No external-user, other-machine or multi-monitor validation. / 本地 24 项测试通过，已检查界面截图，尚未进行外部用户、其他电脑或多显示器验证。

## v0.2.0-alpha.1 — Record review / 记录复核

- Added measurement, deviation and overdue-action detail queries and three hashed detail CSV exports. Detail rows retain batch IDs and relevant dates. / 新增三类记录明细查询与 CSV 导出，保留批次编号和相关日期。
- Summary rows open record windows by double-click or the Details button. Chinese/English headings, status filtering, record search and visible/full-group counts support review. / 双击汇总或点击明细按钮即可复核，支持双语字段、状态筛选、搜索与数量对照。
- Detail views use the completed snapshot rather than changed input files or an edited date field. Future source closure/completion dates remain distinct from the as-of status. / 明细固定使用已完成的快照，源关闭/完成日期与截至日期状态分开呈现。
- Cancelled scheduled GUI polling when the main window is destroyed. / 关闭主窗口时取消待执行的界面轮询。
- Validation: 17 local automated tests passed, including summary/detail reconciliation at two dates and desktop interaction. No external or clean-machine validation. / 本地 17 项测试通过，含两个日期的明细对账与桌面交互；未进行外部或干净机器验证。

## v0.1.0-alpha.1 — Initial local prototype / 首版本地原型

- Added reproducible synthetic data, a four-table SQLite model, input checks and three analyses with an explicit as-of date. / 提供可复现模拟数据、四表 SQLite 模型、输入检查和三个指定日期分析。
- Added a local desktop launcher, bilingual summaries, data dictionary and business brief. / 提供桌面入口、双语摘要、数据字典和业务解释。
- Validation: 12 local tests passed. / 本地 12 项测试通过。
