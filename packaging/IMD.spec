# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path.cwd()
datas = [
    (str(project_root / "web"), "web"),
    (str(project_root / "config.sample.yaml"), "."),
    (str(project_root / "spotify_secrets.sample.yaml"), "."),
]

ffmpeg_dir = project_root / "vendor" / "ffmpeg"
if ffmpeg_dir.exists():
    datas.append((str(ffmpeg_dir), "vendor/ffmpeg"))

hiddenimports = []
for package in ("yt_dlp", "mutagen", "librosa"):
    hiddenimports.extend(collect_submodules(package))


a = Analysis(
    [str(project_root / "imd_launcher.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IMD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="IMD",
)
