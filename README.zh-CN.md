# BatchScope

查看模拟批次的检验结果、未关闭偏差和逾期措施。

[下载 Windows 版](https://github.com/rayexzh/batchscope/releases) · [English](README.md) · [操作说明](docs/INDEX.md)

- 检查输入文件、数值、关联编号和检验范围差异。
- 对比日期，按批次查看记录。
- 修改模拟数据，练习二次、三次检验。
- 复核审计日志，搜索记录，导出报告。

本机运行，支持中英文。仅用模拟数据，不用于真实批次放行。

## 使用

1. 下载并完整解压 ZIP，打开 `BatchScope.exe`。
2. 点击「生成演示数据」，再点「检查输入数据」。
3. 日期填 `2026-06-30`，点击「运行分析」。

![数据实验室](docs/screenshots/laboratory-en.png)

## 从源码运行

需要带 Tkinter 的 Python 3.10 或以上版本：

```powershell
python app.py
```

[输入文件格式](DATA_DICTIONARY.md) · [更新记录](CHANGELOG.md) · [MIT 许可](LICENSE)

检查 NHS 药品 CSV：[RxDataLint](https://github.com/rayexzh/rx-data-lint)。
