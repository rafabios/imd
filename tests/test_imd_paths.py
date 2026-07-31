from pathlib import Path

import imd_paths


def test_macos_uses_application_support_for_writable_runtime_files(tmp_path):
    expected = tmp_path / "Library" / "Application Support" / "IMD Insane Music Downloader"

    assert imd_paths.macos_app_data_dir(tmp_path) == expected
    assert imd_paths.frozen_app_data_dir("/Applications/IMD.app/Contents/MacOS/IMD", "darwin").name == "IMD Insane Music Downloader"


def test_default_user_folders_are_platform_neutral(tmp_path):
    assert imd_paths.default_music_dir(tmp_path) == tmp_path / "Music" / "IMD"
    assert imd_paths.default_state_dir(tmp_path) == tmp_path / "Music" / "IMD-State"


def test_non_macos_frozen_app_keeps_executable_directory():
    path = imd_paths.frozen_app_data_dir("C:/Users/test/AppData/Local/IMD/IMD.exe", "win32")

    assert path == Path("C:/Users/test/AppData/Local/IMD")
