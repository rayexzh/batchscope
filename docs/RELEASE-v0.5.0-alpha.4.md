# BatchScope v0.5.0-alpha.4 / 快照输入与窄窗口修复

Download **BatchScope-0.5.0-alpha.4-windows-x64.zip**, extract fully and run **BatchScope.exe**. Generate demo data, use **2026-06-30**, then Analyse. / 下载、完整解压、双击运行；无需 Python。

- Date controls wrap on narrow windows so comparison and result buttons keep full labels. / 日期操作在窄窗口自动换行。
- Completed snapshots show their original input folder. Changing input/date or generating a new dataset displays **not analysed yet**; old reports and fixed snapshot dates are preserved. / 新输入或日期明确提示未分析，保留旧快照与报告。
- Calculations and synthetic data generation are unchanged. / 不改变指标和模拟数据生成规则。

**Verification:** 47 local source tests passed. Packaged diagnostics include input-change context, small-window date labels, SQL/report/hash workflows and snapshot comparisons. See BUILD.json, EXE_VERIFICATION.json and SHA256SUMS.txt for the actual archive checks. These are build-host/extracted-EXE checks with system-only PATH, not a separate clean-machine trial. The executable is unsigned. / 本地 47 项测试通过，EXE 核对证据见附件；未做独立纯净机器测试，程序未签名。

The patch follows an [AI-scripted desktop simulation](https://github.com/rayexzh/batchscope/blob/main/docs/SIMULATED-USABILITY-REVIEW.md), not a real teacher/user trial. Fictional inputs and illustrative ranges cannot establish GMP/CSV compliance, CAPA effectiveness or batch-release suitability. / 明确模拟试用与数据边界。

[Historical English tutorial](https://github.com/rayexzh/batchscope/blob/main/docs/DEMO_VIDEO.md) remains labelled alpha.2. / 保留旧版演示并标明版本。
