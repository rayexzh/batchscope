# BatchScope

View sample batch test results, open deviations and overdue actions.

[Windows download](https://github.com/rayexzh/batchscope/releases) · [中文](README.zh-CN.md) · [User guide](docs/INDEX.md)

- Check input files, numbers, linked IDs and differing test ranges.
- Compare dates and trace records to their batch.
- Change sample data and practise two- or three-attempt tests.
- Review audit logs, search records and export reports.

Runs locally in English or Chinese. Uses fictional data; not for real batch release.

## Use

1. Download and fully extract the ZIP. Open `BatchScope.exe`.
2. Click **Generate demo data**, then **Check input data**.
3. Set the date to `2026-06-30` and click **Analyse**.

![Data laboratory](docs/screenshots/laboratory-en.png)

## Run from source

Python 3.10+ with Tkinter:

```powershell
python app.py
```

[Input files](DATA_DICTIONARY.md) · [Changes](CHANGELOG.md) · [MIT licence](LICENSE)

For NHS medicines CSVs: [RxDataLint](https://github.com/rayexzh/rx-data-lint).
