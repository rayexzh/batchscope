# BatchScope

一个查看模拟批次质量数据的桌面小工具。能看检验结果、哪些偏差没关、哪些措施逾期。

也可以比较不同日期，或去数据实验室改一个数，看看结果怎么变。原始数据不会跟着改。自带数据都是虚构示例，用来学习和试用，不用于真实批次放行。

[下载 Windows 版](https://github.com/rayexzh/batchscope/releases) · [English](README.md) · [操作说明](docs/INDEX.md)

## 先试一下

1. 下载 ZIP，完整解压，打开 `BatchScope.exe`。
2. 点击「生成演示数据」，再点「检查输入数据」，看看文件、数值和记录有没有需要处理的地方。
3. 日期填 `2026-06-30`，点击「运行分析」。
4. 打开一条记录查看对应批次，或进入「质量数据实验室」，试改检验值、范围和日期。

实验室还可以练习二次、三次检验。首次和后续每轮结果都会保留；多测几次或把范围收窄，不代表结果就更准确。

实验室窗口里切换记录会保留各自的草稿；复检计划改过后，需要重新评价才能导出。

![数据实验室](docs/screenshots/laboratory-en.png)

程序在本机运行，支持中英文、搜索、日期对比和报告导出。空白结果不补零，疑似重复记录只提示核对，不自动删除。

同类检验的范围不一样时，会列出两条记录供核对，不替你决定该用哪个规格。

## 从源码运行

需要带 Tkinter 的 Python 3.10 或以上版本：

```powershell
python app.py
```

不需要付费 API。[输入文件格式](DATA_DICTIONARY.md) · [输入预检](docs/INPUT_CHECK.md) · [实验室用法](docs/LABORATORY.md) · [更新记录](CHANGELOG.md) · [MIT 许可](LICENSE)

[RxDataLint](https://github.com/rayexzh/rx-data-lint) 是另一个独立工具，负责检查 NHS 药品 CSV。
