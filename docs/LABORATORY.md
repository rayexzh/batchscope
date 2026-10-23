# Quality data laboratory / 质量数据实验室

Change a synthetic result, its fictional bounds or measurement date and compare the outcome. Both scenarios use the same as-of date. The laboratory copies a completed analysis snapshot; it never edits the original CSVs, database or main-window results.

修改模拟检验值、示例范围或检验日期，观察结果如何变化。两种情景共用一个截至日期。实验室从已完成分析复制快照，不改原始 CSV、数据库或主界面结果。

![Scenario comparison](screenshots/laboratory-en.png)

## Try an experiment / 做一次实验

1. Generate demo inputs and run the main analysis. Open **Quality data laboratory**. / 生成模拟数据并完成主分析，打开「质量数据实验室」。
2. Search for a test or batch. Select its row and edit the result, bounds or date. A blank result means missing; zero is a measured value. / 搜索检验或批次，选中一行后修改。空白表示缺失，零是实际模拟数值。
3. Choose **Stage / update change**. You can stage several records before running. **Restore selected** removes that record's queued edits. / 点击「加入 / 更新修改」，可累计多条修改；「恢复选中记录」移除该记录的修改。
4. Set the shared as-of date and **Run comparison**. Read the baseline, scenario and change counts, then scroll to the record-level settings. / 设置共用截至日期并运行，查看原始、假设及净变化，再查看记录级修改。
5. **Export experiment** saves the last current calculation. Changing staged settings or the date disables export until you run again. / 导出保存当前计算；修改已加入的设置或日期后需重新运行，不能把旧结果当新结果导出。

Changes in counts need context. Moving a measurement beyond the as-of date removes it from that date's denominator; it does not demonstrate better quality. Changing a bound is a hypothetical exercise, never an approved specification change. Tests outside a range do not automatically create deviations or actions.

数量变化需要结合条件阅读。把检验日期移到截至日期之后，会减少当日统计记录，不代表质量改善；修改范围仅是假设，不是批准规格。超范围不会自动生成偏差或措施。

## Drafts / 草稿

Drafts stay with each test while this laboratory window remains open. Switching records or changing language does not discard them. If another record has pending edits, its ID is shown in the status. Stage or restore main edits before calculating; evaluate changed repeat plans before exporting. Close confirmation includes pending forms across all visited records. Drafts are held in memory, not saved to disk.

实验室窗口打开期间，各条检验保留自己的草稿；切换记录或语言不会丢掉输入。其他记录还有草稿时，状态栏显示其编号。主表单需先加入队列或恢复，再计算；复检计划改过后需重新评价，才能导出。关闭确认也检查其他记录的草稿。草稿暂存在内存中，不是落盘保存。

Changing a repeat value, bound, date, attempt count or reason marks the plan pending. A failed evaluation keeps the previous evaluated attempts and the changed draft. Returning to a record shows its own last evaluated attempts. A later successful evaluation adds another retained exercise; it does not overwrite the earlier one. **Restore selected** discards that record's current forms and queued edits. **Reset entire experiment** clears all drafts, queued edits and exercises in this window.

复检值、范围、日期、轮次或理由改动后，计划会标记为未评价。评价失败会保留旧结果及新草稿。切回记录时显示该记录自己的上次评价；再次评价成功会保留一份新练习，不覆盖此前练习。「恢复选中记录」丢弃该记录当前表单及排队修改；「清空实验」清除本窗口所有草稿、排队修改和练习。

## Two- and three-attempt practice / 二次、三次检验练习

Select a test in the editing tab, then open **Recheck exercise**. The original result, bounds and date are shown before you enter the plan. Choose two or three total attempts, provide a reason, then enter all additional results, bounds and dates before evaluating.

先在编辑页选中检验，再进入「重复检验练习」。界面先显示保留的初始结果及范围、日期；选择总轮次、填写练习理由，录入后续各轮条件，再统一评价。

- Attempt 1 always keeps the source result. Later within-range results never erase it. / 第 1 轮始终保留原始结果，后续范围内结果不能抹去它。
- Dates cannot go backwards. Teaching ranges may stay equal or narrow; widening is rejected in this exercise. Narrower is not automatically more accurate. / 日期不能倒退；练习范围可保持或收窄，不能放宽。收窄不等于更准确。
- Every attempt is shown separately. No average, majority vote, final-pass score or batch-release verdict is produced. / 每轮单独显示，不取平均、不多数投票、不生成最终合格分数或批次放行结论。
- Repeat exercises are separate from scenario metrics. They do not insert new measurements into the main database. / 重复练习与情景指标分开，不向主数据库插入新检验。

![All attempts retained](screenshots/laboratory-recheck-en.png)

This is a teaching exercise, not a real OOS investigation, approved retest plan, validated LIMS or laboratory procedure. FDA's OOS guidance rejects repeatedly testing until a passing result appears and disregarding an initial OOS result without scientific justification. Follow the applicable approved procedures and responsible quality review for real work. [FDA OOS guidance, May 2022](https://www.fda.gov/media/158416/download).

这是教学练习，不是真实 OOS 调查、获批复检计划、经验证的 LIMS 或实验室规程。上述 FDA 指导不支持反复检到合格后、在无科学依据时忽略原始超规格结果。实际工作应使用适用的批准程序及质量审核。

## Export and replay / 导出与重跑

The export contains `EXPERIMENT.json`, metrics and record-change CSVs, Chinese/English HTML reports, and separate `baseline/` and `scenario/` input folders. Repeat exercises, if present, include all attempts and their recorded plans. The completion manifest is written last and records file hashes. An interrupted export without that manifest is incomplete. Hashes identify bytes; they do not authenticate a reviewer or certify regulatory compliance.

导出包含实验 JSON、指标与记录变化 CSV、中英文 HTML，以及原始 / 假设两份输入。重复练习保留各轮结果及计划。完成清单最后写入，记录文件哈希；缺少完成清单的中断导出不完整。哈希只标识文件内容，不认证人员或证明合规。

```powershell
python quality_ops.py analyse <experiment>/baseline <new-baseline-output> --as-of 2026-06-30
python quality_ops.py analyse <experiment>/scenario <new-scenario-output> --as-of 2026-06-30
```

Use the as-of date stored in `EXPERIMENT.json` and new output folders. **Reset entire experiment** clears queued edits and practice results; it does not delete exports or source files. / 使用实验 JSON 中的截至日期及新的输出目录。「清空实验」清除排队修改和练习结果，不删除已导出文件或原始数据。


## Save progress / 保存进度

Click **Save progress** to save a new `.bslab` file. It includes the baseline snapshot, staged changes, unfinished forms and evaluated attempts. On the main window, **Open lab progress** reopens it without the original output folder. Run comparison again before exporting. Existing progress files are not overwritten; choose a new name. After saving, you can close without a discard warning; new edits trigger it again. Two-attempt plans keep their evaluated state when reopened.

点「保存进度」保存为新的 `.bslab` 文件，包含基准数据、排队修改、未完成表单和已评价轮次。下次在主窗口点「打开实验室进度」，不需要原输出文件夹。恢复后重新运行对比，再导出结果。已有进度文件不会覆盖，请另取名字。保存后关闭不再误报丢弃修改；继续编辑后会重新提醒。两轮复检恢复后保留已评价状态。

Progress is an editable working file, not an approved record or completed report. The snapshot checksum detects changed bytes; it does not authenticate the author.

进度是可编辑的工作文件，不是批准记录或已完成报告。快照校验值用于检查文件内容，不认证作者。

## Decimal values / 小数

Results and limits retain their input text. Comparisons use decimal values, so `94.999999999999999` is below `95`. Boundaries are inclusive. JSON stores these values as strings. For direct SQLite queries, call `decimal_values.configure(connection)` before running the supplied SQL. Do not cast results to REAL before comparing. Older databases already stored as REAL cannot recover lost digits; analyse the original CSV again.

检验值和上下限保留输入文本，按十进制比较。例如 `94.999999999999999` 小于 `95`；恰好等于上下限仍算范围内。JSON 中这些数值是字符串。直接查询 SQLite 前，调用 `decimal_values.configure(connection)`，不要转成 REAL 再比较。旧数据库已丢失的小数位无法恢复，请用原 CSV 重新分析。
