# BatchScope v0.5.0-alpha.3 / 批次质量洞察

Download **BatchScope-0.5.0-alpha.3-windows-x64.zip**, extract completely and run **BatchScope.exe**. Click Generate, use **2026-06-30**, then Analyse. The package is independent of RxDataLint and needs no Python or paid API. / 下载、完整解压、双击程序；独立于 Rx 运行。

## Changes / 本次变化

- Invalid calendar dates and reversed comparison dates are rejected before clearing the last successful snapshot or creating a run folder. Old dates remain explicit. / 日期提前校验，保留旧结果和快照日期。
- The action filter is hidden on age/month views, which use the full snapshot; its choice is restored when returning to actions. / 措施筛选仅在适用页显示。
- Standalone quick-start, bilingual homepage and documentation index. / 独立启动指南、双语首页与导航。
- [English demo recorded on alpha.2](https://github.com/rayexzh/batchscope/blob/main/docs/DEMO_VIDEO.md) remains available. The two usability issues in the historical [AI-simulated review](https://github.com/rayexzh/batchscope/blob/main/docs/teacher-review/REPORT.zh-CN.md) are now addressed; no real teacher participated. / 保留旧版本演示；历史模拟评审标明修复状态，不声称真实老师认可。

## Verification / 验证

45 local source tests passed. The ZIP-extracted EXE passed its workflow/SQL/report/hash checks from a separate temporary Chinese/spaced path, with relative and absolute self-test folders and no Python directory in PATH. See **EXE_VERIFICATION.json**, **BUILD.json** and **SHA256SUMS.txt**. These are build-host checks, not an independent clean-machine test. The executable is unsigned.

本地 45 项测试通过，实际解压后的 EXE 完成自检；未做独立纯净机器测试，程序未签名。

The project uses fictional synthetic inputs and illustrative ranges only. It is an educational quality-operations prototype; it does not certify GMP/CSV compliance, release batches, assess CAPA effectiveness or predict clinical risk. / 仅模拟教学与作品集原型。
