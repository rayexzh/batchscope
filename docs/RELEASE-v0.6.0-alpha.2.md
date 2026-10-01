# BatchScope v0.6.0-alpha.2

Record what happened after an audit finding was reviewed. / 记录审计检查项复核后的处理状态和理由。

- Four statuses: not reviewed, in review, retained for follow-up, explained without follow-up. / 四种状态：未复核、正在复核、保留需跟进、已说明无需跟进。
- Reviewer name and reason; local revision history; status filtering and note search. / 复核人、理由、本地修改版本、状态筛选与备注搜索。
- Notes return when reopening the same source bytes, policy and ruleset. Stale editors cannot overwrite newer saves. / 相同文件、配置与规则版本可恢复；旧编辑窗口不能覆盖新记录。
- Full exports retain all findings and add notes/history to JSON, CSV, SQLite and bilingual HTML. / 完整导出保留全部检查项，并附复核记录与历史。

Download and extract **BatchScope-0.6.0-alpha.2-windows-x64.zip**, then open **BatchScope.exe**. In Audit log review, select a finding and choose **Add review note**. / 下载并完整解压后双击 EXE，在审计窗口选择检查项，点击填写复核记录。

66 local tests passed. Packaged checks cover save, reopen and export as well as the existing quality and timeline workflows. / 本地 66 项测试通过，EXE 检查涵盖备注保存、恢复、导出及既有流程。

Notes are stored separately from source logs. Names are self-entered, not authenticated signatures; local revision history is not tamper-proof. A status does not change rule findings or certify compliance. Unsigned Windows prototype, synthetic data only. / 备注与原日志分开。姓名为手动填写，本地历史不是防篡改审计追踪，状态不改变检查结果或认证合规。EXE 未签名，仅模拟原型。

[Review instructions / 操作说明](https://github.com/rayexzh/batchscope/blob/main/docs/REVIEW_NOTES.md) · [78-second animation, previous version / 上一版短动画](https://github.com/rayexzh/batchscope/releases/download/v0.6.0-alpha.1/BatchScope-Short-Explainer.mp4)
