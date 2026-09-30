# Windows portable build / Windows 便携版打包

Download a release ZIP, extract it, then double-click `BatchScope.exe`. No Python installation is needed. Outputs persist under `%LOCALAPPDATA%\BatchScope\outputs`. Keep the ZIP and checksum if you need to identify the downloaded build.

普通用户只需下载并解压发布 ZIP，双击 EXE，无需安装 Python。输出保存在上述用户目录。

## Build from source / 从源码打包

Use Windows x64 with Python 3.14 and Tkinter. Build dependencies are isolated from runtime requirements. PyInstaller is pinned in `requirements-build.txt`; see its [official packaging guide](https://pyinstaller.org/en/stable/usage.html) and [resource-path documentation](https://pyinstaller.org/en/stable/runtime-information.html).

从项目目录运行：

```powershell
python -m venv outputs/build-env
.\outputs\build-env\Scripts\python.exe -m pip install -r requirements-build.txt
.\outputs\build-env\Scripts\python.exe build_windows.py
```

The `dist/` directory contains the EXE, portable ZIP, SHA-256 checksums and `BUILD.json`. `build/`, `dist/` and temporary build environments are excluded from source control. Release binaries belong in GitHub Releases, not in the Git repository.

`dist/` 提供 EXE、便携 ZIP、校验文件与构建信息；生成物不进入源码仓库，二进制放在 GitHub Releases。

Bundled schema/SQL files are read-only resources. EXE output uses the user profile, not the temporary one-file extraction folder or the installation directory. The portable archive also includes source, fictional inputs, documentation and applicable runtime notices. The executable is not digitally signed.

内置 SQL 与数据库结构只读；输出不依赖临时解压目录或安装目录。便携包附带源码、模拟输入、文档和运行时声明，EXE 未做数字签名。

## Verify the packaged program / 验证打包程序

Choose a new test output directory, then run:

```powershell
$process = Start-Process -FilePath .\dist\BatchScope.exe -ArgumentList @('--self-test', 'build\exe-check') -Wait -PassThru -WindowStyle Hidden
$process.ExitCode
Get-Content build\exe-check\SELF_TEST.json
```

The self-test exercises embedded SQL resources, known June/July metrics, comparisons, work-queue reconciliation, hashes, the native Generate/Analyse workflow, workbench/batch windows and language/theme switching. It uses an isolated user-output profile under the specified test folder and writes `SELF_TEST.json` with pass/fail status. This is software verification, not GMP/CSV validation or proof of operation on every Windows computer.

自检检查内置 SQL、已知指标、日期对比、队列对账、哈希、生成/分析按钮流程、工作台与批次窗口、语言主题，输出 JSON 证据。自检的用户输出目录隔离在指定测试文件夹内，不污染日常结果。这是软件验证，不是 GMP/CSV 验证，也不证明所有 Windows 电脑均兼容。

The **Windows EXE** workflow builds and checks a portable artifact on tagged releases or manual dispatch. The published release includes the maintainer-built asset and its verification evidence; a separate CI build can have a different hash.

标签或手动触发 Windows EXE 工作流，自动构建并自检；发布资产提供实际上传包的校验与验证证据，另一次 CI 构建的哈希可能不同。
