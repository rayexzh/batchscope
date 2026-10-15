# BatchScope

A desktop app for looking through sample batch records: test results, open deviations and overdue actions.

You can compare dates, follow a record back to its batch, or try a change in the data laboratory. The original data stays unchanged. The included data is fictional; this is a learning tool, not a batch-release system.

[Windows download](https://github.com/rayexzh/batchscope/releases) · [中文](README.zh-CN.md) · [Guides](docs/INDEX.md)

## Try it

1. Download and fully extract the ZIP, then open `BatchScope.exe`.
2. Click **Generate demo data**, then **Check input data**. The check lists missing files, bad values and records that need a closer look.
3. Set the date to `2026-06-30` and click **Analyse**.
4. Open a record to see its batch, or use **Quality data laboratory** to try changing a result, range or date.

The laboratory also has a two-/three-attempt exercise. Every result stays visible, including an initial result outside the range. More attempts or narrower ranges do not automatically mean greater accuracy.

![Data laboratory](docs/screenshots/laboratory-en.png)

The app runs locally. It has Chinese and English interfaces, search, date comparisons and report exports. Missing results stay missing. Possible duplicates are listed for review and are not deleted.

If comparable tests use different ranges, the check lists both for review. It does not choose a specification for you.

## Run from source

Python 3.10+ with Tkinter:

```powershell
python app.py
```

No paid API is needed. [Input files](DATA_DICTIONARY.md) · [Input check](docs/INPUT_CHECK.md) · [Laboratory](docs/LABORATORY.md) · [Changes](CHANGELOG.md) · [MIT licence](LICENSE)

[RxDataLint](https://github.com/rayexzh/rx-data-lint) is a separate app for checking NHS medicines CSVs.
