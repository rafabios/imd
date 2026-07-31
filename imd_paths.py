import sys
from pathlib import Path
from typing import Optional


APP_DATA_DIR_NAME = "IMD Insane Music Downloader"


def macos_app_data_dir(home: Optional[Path] = None) -> Path:
    user_home = Path(home) if home is not None else Path.home()
    return user_home / "Library" / "Application Support" / APP_DATA_DIR_NAME


def default_music_dir(home: Optional[Path] = None) -> Path:
    user_home = Path(home) if home is not None else Path.home()
    return user_home / "Music" / "IMD"


def default_state_dir(home: Optional[Path] = None) -> Path:
    user_home = Path(home) if home is not None else Path.home()
    return user_home / "Music" / "IMD-State"


def frozen_app_data_dir(executable: str, platform: Optional[str] = None) -> Path:
    current_platform = platform or sys.platform
    if current_platform == "darwin":
        return macos_app_data_dir()
    return Path(executable).resolve().parent
