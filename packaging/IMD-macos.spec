# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path.cwd()
product_version = os.environ.get("PRODUCT_VERSION", "0.0.0")
ffmpeg_dir = Path(os.environ["FFMPEG_DIR"])

datas = [
    (str(project_root / "web"), "web"),
    (str(project_root / "config.sample.yaml"), "."),
    (str(project_root / "spotify_secrets.sample.yaml"), "."),
]
binaries = [
    (str(ffmpeg_dir / "ffmpeg"), "vendor/ffmpeg"),
    (str(ffmpeg_dir / "ffprobe"), "vendor/ffmpeg"),
]

hiddenimports = []
for package in ("yt_dlp", "mutagen", "librosa", "openpyxl"):
    hiddenimports.extend(collect_submodules(package))


a = Analysis(
    [str(project_root / "imd_launcher.py")],
    pathex=[str(project_root)],
    binaries=binaries,
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
    upx=False,
    console=False,
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
    upx=False,
    name="IMD",
)

app = BUNDLE(
    coll,
    name="IMD.app",
    icon=None,
    bundle_identifier="br.tec.vemcompy.imd",
    version=product_version,
    info_plist={
        "CFBundleDisplayName": "IMD Insane Music Downloader",
        "CFBundleName": "IMD",
        "NSHighResolutionCapable": True,
    },
)
