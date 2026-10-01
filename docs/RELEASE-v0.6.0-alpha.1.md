# BatchScope v0.6.0-alpha.1

## Changes / 更新

- Review synthetic audit events for missing reasons, permission mismatches and timestamp issues. Inspect source evidence, search by user/event/batch, and export complete reports. / 复核模拟操作日志的原因缺失、权限不匹配及时间异常，支持原始操作、搜索和完整导出。
- Compare 2–12 dates. Quality views show each snapshot and adjacent movements; audit views count dated events and list invalid timestamps separately. / 对比 2–12 个日期，查看质量快照与相邻变化；审计事件按日期统计，无效时间戳单列。
- Includes a 78-second animated explainer, English voice/captions and Chinese chapter text. / 提供 78 秒动画，含英文旁白、字幕及中文章节说明。

## Download / 下载

Extract **BatchScope-0.6.0-alpha.1-windows-x64.zip** completely and open **BatchScope.exe**. Python and paid APIs are not required. Earlier releases remain available. / 完整解压后双击 EXE，不需要 Python 或付费 API，旧版本保留。

From the main window, generate quality data and run an analysis. Open **Multi-date review** to compare dates; open **Audit log review** and generate its sample log for audit review. / 主界面生成质量数据并运行分析；多日期入口用于对比，审计入口可生成独立模拟日志。

## Checks / 核对

60 local automated tests cover existing workflows and the new modules. The packaged EXE self-test covers audit generation/export, undated events and multi-date quality results. File hashes and build details are supplied with the release. / 本地 60 项测试覆盖旧流程与新模块；EXE 自检包含日志生成与导出、无日期事件及多日期质量结果，发布附件含哈希与构建信息。

## Scope / 边界

Synthetic prototype. Configured permissions and UTC working hours are examples, not regulatory requirements. Flags prompt review and do not establish a violation. Date comparisons use one input snapshot and do not reconstruct edit history. The executable is unsigned; checks on the build host do not constitute independent clean-machine testing. / 模拟原型，权限和 UTC 工作时间为示例而非法规。标记提示复核，不判定违规；日期对比不是编辑历史。EXE 未签名，构建机检查不代表独立新机器测试。
