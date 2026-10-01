# BatchScope

Review synthetic batch tests, open deviations and overdue actions at a chosen date.

用模拟数据查看批次检验、未关闭偏差和逾期措施，支持两个日期的变化对比。[完整中文说明](README.zh-CN.md)

[Windows download](https://github.com/rayexzh/batchscope/releases/tag/v0.5.0-alpha.4) · [Documentation](docs/INDEX.md) · [English demo](docs/DEMO_VIDEO.md)

**Current version: v0.5.0-alpha.4.** A local desktop demonstration using synthetic data only.

## What it is for

Batch tests, deviations and follow-up actions are related, but looking at separate tables can hide that relationship. A deviation may be closed while its actions are still outstanding. Today's status can also give the wrong answer to a question about last month.

BatchScope links these records and shows their state at an explicit **as-of date**. It is designed for learning pharmaceutical quality workflows and demonstrating how Python and SQL can support record review.

![Two-date comparison](docs/screenshots/comparison-zh.png)

## What you can inspect

| View | Question |
|---|---|
| **Test ranges** | Which available results fall outside the configured fictional ranges? Which results are missing? |
| **Deviation backlog** | Which deviations were still open on the selected date, and how old were they? |
| **Action follow-up** | Which outstanding actions were overdue? Which batch and deviation do they belong to? |
| **Date comparison** | What opened, closed or became overdue between two dates? |

Open a record to follow its links to the batch, measurements, deviations and actions. Tables support search, sorting and copying. The interface offers Chinese/English switching, themes and font-size controls.

## Try the built-in example

1. Download the Windows ZIP, **extract it completely**, and run **BatchScope.exe**. Python is not required.
2. Click **Generate demo data**.
3. Set the as-of date to **2026-06-30** and click **Analyse**.
4. Open a record and follow it back to its batch.
5. Compare **2026-06-30 → 2026-07-31**, then open the report or results folder.

The default example gives these results:

| Metric | 30 June | 31 July |
|---|---:|---:|
| Open deviations | 22 | 17 |
| Overdue actions | 30 | 33 |

The overdue count rises despite fewer open deviations: four actions become overdue and one is resolved. The comparison includes these changes, rather than just two totals. These are deliberately constructed teaching data, not company performance figures.

Editing a date or input folder does not recalculate a completed result. Run the analysis again; the previous result stays tied to its original snapshot.

## Inputs and outputs

The example generator creates `batches.csv`, `test_results.csv`, `deviations.csv` and `actions.csv`, with a `SOURCE.json` declaration. See the [data dictionary](DATA_DICTIONARY.md) for fields and relationships.

Each completed run produces a SQLite database, CSV summaries and details, an offline report, and run metadata. In the Windows application, generated data and results are saved under `%LOCALAPPDATA%\BatchScope\outputs`. No paid API is needed.

## Scope

Configured ranges are fictional. A range flag or overdue action calls for review; it does not establish root cause, certify compliance or authorise batch release. The program has no electronic signatures or production access-control system. It is not a validated replacement for a pharmaceutical quality-management system.

The Windows executable is unsigned. Tests and scripted usability checks are documented, but no external deployment or teacher endorsement is claimed. See the [quality review notes](docs/QUALITY_REVIEW.md) and [scripted usability review](docs/SIMULATED-USABILITY-REVIEW.md).

## Run from source

Use Python 3.10+ with Tkinter. Run from the repository root:

```powershell
python app.py
```

For command-line generation and analysis, see the [startup guide](docs/QUICKSTART.md) and project documentation. The core application uses Python's standard library and SQLite.

## Further reading

- [Date comparisons](docs/COMPARISON.md) and [interface guide](docs/INTERFACE.md)
- [Business example](BUSINESS_BRIEF.md) and [SQL case study](docs/CASE_STUDY.md)
- [Changes](CHANGELOG.md) and [contributing](CONTRIBUTING.md)
- [English demo](docs/DEMO_VIDEO.md) — an edited walkthrough of v0.5.0-alpha.2 with synthesized narration.

Software licence: [MIT](LICENSE). [RxDataLint](https://github.com/rayexzh/rx-data-lint) is maintained separately and checks NHS medicines CSVs; it is not required to run BatchScope.
