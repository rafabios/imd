import os
import sys
from pathlib import Path
from typing import Optional


APP_DATA_DIR_NAME = "IMD Insane Music Downloader"


def macos_app_data_dir(home: Optional[Path] = None) -> Path:
    user_home = Path(home) if home is not None else Path.home()
    return user_home / "Library" / "Application Support" / APP_DATA_DIR_NAME


def windows_music_folder(home: Optional[Path] = None) -> Path:
    if home is not None:
        return Path(home) / "Music"

    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "My Music")
        expanded = os.path.expandvars(str(value).strip())
        if expanded and "%" not in expanded:
            return Path(expanded)
    except (ImportError, OSError, ValueError):
        pass

    return Path.home() / "Music"


def default_music_dir(home: Optional[Path] = None, platform: Optional[str] = None) -> Path:
    current_platform = platform or sys.platform
    if current_platform == "win32":
        return windows_music_folder(home) / "IMD"
    user_home = Path(home) if home is not None else Path.home()
    return user_home / "Music" / "IMD"


def legacy_default_state_dir(home: Optional[Path] = None) -> Path:
    user_home = Path(home) if home is not None else Path.home()
    return user_home / "Music" / "IMD-State"


def default_state_dir(
    home: Optional[Path] = None,
    platform: Optional[str] = None,
    local_app_data: Optional[Path] = None,
) -> Path:
    current_platform = platform or sys.platform
    user_home = Path(home) if home is not None else Path.home()
    if current_platform == "win32":
        if local_app_data is not None:
            data_root = Path(local_app_data)
        elif home is None and os.environ.get("LOCALAPPDATA"):
            data_root = Path(os.environ["LOCALAPPDATA"])
        else:
            data_root = user_home / "AppData" / "Local"
        return data_root / APP_DATA_DIR_NAME / "state"
    if current_platform == "darwin":
        return macos_app_data_dir(user_home) / "state"

    if home is None and os.environ.get("XDG_STATE_HOME"):
        data_root = Path(os.environ["XDG_STATE_HOME"])
    else:
        data_root = user_home / ".local" / "state"
    return data_root / APP_DATA_DIR_NAME


def frozen_app_data_dir(executable: str, platform: Optional[str] = None) -> Path:
    current_platform = platform or sys.platform
    if current_platform == "darwin":
        return macos_app_data_dir()
    return Path(executable).resolve().parent
