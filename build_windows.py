"""Build a Windows x64 portable EXE and archive, using an isolated build environment."""
import hashlib
from importlib.metadata import distribution
import json
import struct
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from quality_ops import VERSION


def main():
    if sys.platform != "win32":
        raise SystemExit("Build on Windows; PyInstaller does not cross-compile.")
    if struct.calcsize("P") != 8:
        raise SystemExit("Use 64-bit Python to build the Windows x64 package.")
    root = Path(__file__).resolve().parent
    build, dist = root / "build", root / "dist"
    args = [sys.executable,"-m","PyInstaller","--noconfirm","--clean","--onefile","--windowed",
            "--name","BatchScope","--distpath",str(dist),"--workpath",str(build / "pyinstaller"),
            "--specpath",str(build),"--add-data",f"{root / 'schema.sql'};.",
            "--add-data",f"{root / 'sql'};sql","--add-data",f"{root / 'detail_sql'};detail_sql",
            "--add-data",f"{root / 'operations_sql'};operations_sql",str(root / "app.py")]
    subprocess.run(args, cwd=root, check=True)
    exe = dist / "BatchScope.exe"
    package = build / f"BatchScope-{VERSION}-windows-x64"
    package.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(exe, package / exe.name)
    for pattern in ("*.py","*.md","*.json","*.txt","*.sql","*.bat"):
        for p in root.glob(pattern):
            if p.is_file():
                shutil.copyfile(p, package / p.name)
    shutil.copyfile(root / "LICENSE", package / "LICENSE")
    for name in ("examples","docs","sql","detail_sql","operations_sql"):
        shutil.copytree(root / name, package / name, dirs_exist_ok=True)
    (package / "START_HERE.txt").write_text("BatchScope / 批次质量洞察\n\n1. Extract this ZIP completely. / 完整解压 ZIP。\n2. Double-click BatchScope.exe. Python is not required. / 双击 BatchScope.exe，无需 Python。\n3. Generate synthetic data, then Analyse. / 生成模拟数据后运行分析。\n4. Open Quality review workbench to trace actions and batches. / 打开质量复核工作台查看措施和批次。\n\nOutputs remain in %LOCALAPPDATA%\\BatchScope\\outputs. / 输出保存在该用户目录，不写入临时解压位置。\nSynthetic prototype only; no batch release or compliance certification. / 仅模拟原型，不用于批次放行或合规认证。\n",encoding="utf-8-sig")
    licence = Path(sys.base_prefix) / "LICENSE.txt"
    if licence.is_file():
        shutil.copyfile(licence, package / "PYTHON_LICENSE.txt")
    for i,p in enumerate(sorted((Path(sys.base_prefix) / "tcl").rglob("license.terms"))):
        shutil.copyfile(p, package / f"TCL_TK_LICENSE_{i+1}.txt")
    for dependency in ("pyinstaller", "pyinstaller-hooks-contrib"):
        metadata = distribution(dependency)
        for entry in metadata.files or []:
            if ".dist-info/licenses/" in str(entry) and metadata.locate_file(entry).is_file():
                shutil.copyfile(metadata.locate_file(entry), package / f"{dependency}_{entry.name}")
    archive = dist / f"BatchScope-{VERSION}-windows-x64.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(package.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(package))
    record = {"project":"BatchScope","version":VERSION,"architecture":"Windows x64",
              "python":sys.version,"archive":archive.name,"archive_bytes":archive.stat().st_size,
              "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
              "exe_sha256":hashlib.sha256(exe.read_bytes()).hexdigest()}
    (dist / "BUILD.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    (dist / "SHA256SUMS.txt").write_text(f"{record['archive_sha256']}  {archive.name}\n{record['exe_sha256']}  BatchScope.exe\n",encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__ == "__main__":
    main()
