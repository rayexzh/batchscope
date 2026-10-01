# First example / 第一个示例

1. Download the current Windows ZIP from [BatchScope releases](https://github.com/rayexzh/batchscope/releases), extract it completely and run **BatchScope.exe**. / 下载并完整解压后双击程序。
2. Click **Generate demo data / 生成演示数据**. Inputs are fictional; no NHS CSV is needed. / 这是独立的模拟批次数据，不需要 Rx 或 SCMD 文件。
3. Use **2026-06-30** and click **Analyse / 运行分析**. Expect 198 measurements, 184 judgeable, 14 missing, 74 range flags, 22 open deviations and 30 overdue actions. / 对照这些示例数值。
4. Open the workbench. Trace an action to its batch; inspect tests, deviations and all visible actions. / 从措施追到批次。
5. Compare **2026-06-30 → 2026-07-31**. Open deviations: 22 → 17. Overdue actions: 30 → 33 (4 new, 1 resolved). / 区分总数与变化来源。
6. Open the offline report or result folder. Outputs persist under `%LOCALAPPDATA%\BatchScope\outputs`; no paid API or Python installation is required. / 输出保存在本机。

## Date correction / 日期纠错

Invalid calendar dates or reversed comparison dates are rejected before a new run starts. The last completed result and its snapshot date remain on screen. Correct the entry and rerun; editing dates alone does not update old results. / 无效日期提前阻止运行，旧结果和快照保留；输入新日期后仍需重新运行。

## Scope / 范围

Fictional ranges and overdue lists prompt review; they are not investigation conclusions, batch release decisions or compliance certification. The action filter applies only to Action follow-up and is hidden on full-snapshot age/month views. / 范围标记和逾期是复核线索；措施筛选仅用于措施跟进。
