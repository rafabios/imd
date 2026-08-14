from datetime import date
import hashlib

import pytest

import audio_analysis
import imd_launcher


def test_version_tuple_orders_yt_dlp_versions():
    assert imd_launcher.version_tuple("2026.07.17") > imd_launcher.version_tuple("2025.12.31")
    assert imd_launcher.version_tuple("2026.7.17") == imd_launcher.version_tuple("2026.07.17")


def test_create_initial_config_uses_real_user_directories(monkeypatch, tmp_path):
    sample = tmp_path / "config.sample.yaml"
    target = tmp_path / "config.yaml"
    sample.write_text(
        'paths:\n  music_dir: "C:/Users/SEU_USUARIO/Music/IMD"\n'
        '  state_dir: "C:/Users/SEU_USUARIO/AppData/Local/IMD Insane Music Downloader/state"\n'
        'conversion:\n  music_dir: "C:/Users/SEU_USUARIO/Music/IMD"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(imd_launcher, "default_music_dir", lambda: tmp_path / "Music" / "IMD")
    monkeypatch.setattr(imd_launcher, "default_state_dir", lambda: tmp_path / "AppData" / "Local" / "IMD" / "state")

    imd_launcher.create_initial_config(sample, target)

    content = target.read_text(encoding="utf-8")
    assert (tmp_path / "Music" / "IMD").as_posix() in content
    assert (tmp_path / "AppData" / "Local" / "IMD" / "state").as_posix() in content
    assert "SEU_USUARIO" not in content


def test_update_existing_config_schema_adds_only_missing_fields(tmp_path):
    sample = tmp_path / "config.sample.yaml"
    target = tmp_path / "config.yaml"
    sample.write_text(
        "paths:\n  music_dir: C:/Default\n"
        "ytdlp:\n  format: bestaudio/best\n  candidate_limit: 6\n  spectral_check: true\n",
        encoding="utf-8",
    )
    target.write_text(
        "paths:\n  music_dir: C:/User/Music\n"
        "ytdlp:\n  format: bestaudio[ext=m4a]\n",
        encoding="utf-8",
    )

    backup = imd_launcher.update_existing_config_schema(sample, target)
    updated = imd_launcher.yaml.safe_load(target.read_text(encoding="utf-8"))

    assert backup is not None
    assert backup.is_file()
    assert "C:/User/Music" in backup.read_text(encoding="utf-8")
    assert updated["paths"]["music_dir"] == "C:/User/Music"
    assert updated["ytdlp"]["format"] == "bestaudio[ext=m4a]"
    assert updated["ytdlp"]["candidate_limit"] == 6
    assert updated["ytdlp"]["spectral_check"] is True


def test_update_existing_config_schema_does_nothing_when_complete(tmp_path):
    sample = tmp_path / "config.sample.yaml"
    target = tmp_path / "config.yaml"
    content = "ytdlp:\n  candidate_limit: 6\n"
    sample.write_text(content, encoding="utf-8")
    target.write_text(content, encoding="utf-8")

    backup = imd_launcher.update_existing_config_schema(sample, target)

    assert backup is None
    assert not list(tmp_path.glob("config.pre-schema-*.yaml"))


def test_migrate_legacy_state_directory_copies_history_and_keeps_old_folder(monkeypatch, tmp_path):
    old_state = tmp_path / "Music" / "IMD-State"
    new_state = tmp_path / "AppData" / "Local" / "IMD" / "state"
    old_state.mkdir(parents=True)
    (old_state / "historico.txt").write_text("faixa antiga\n", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        f'paths:\n  music_dir: "{(tmp_path / "Music" / "IMD").as_posix()}"\n'
        f'  state_dir: "{old_state.as_posix()}"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(imd_launcher, "legacy_default_state_dir", lambda: old_state)
    monkeypatch.setattr(imd_launcher, "default_state_dir", lambda: new_state)

    backup = imd_launcher.migrate_legacy_state_directory(config)
    updated = imd_launcher.yaml.safe_load(config.read_text(encoding="utf-8"))

    assert backup is not None and backup.is_file()
    assert updated["paths"]["state_dir"] == new_state.as_posix()
    assert (new_state / "historico.txt").read_text(encoding="utf-8") == "faixa antiga\n"
    assert (old_state / "historico.txt").is_file()


def test_migrate_legacy_state_directory_preserves_custom_location(monkeypatch, tmp_path):
    custom_state = tmp_path / "MeuEstado"
    config = tmp_path / "config.yaml"
    config.write_text(f'paths:\n  state_dir: "{custom_state.as_posix()}"\n', encoding="utf-8")
    monkeypatch.setattr(imd_launcher, "legacy_default_state_dir", lambda: tmp_path / "Music" / "IMD-State")
    monkeypatch.setattr(imd_launcher, "default_state_dir", lambda: tmp_path / "AppData" / "state")

    backup = imd_launcher.migrate_legacy_state_directory(config)

    assert backup is None
    assert imd_launcher.yaml.safe_load(config.read_text(encoding="utf-8"))["paths"]["state_dir"] == custom_state.as_posix()


def test_main_routes_packaged_analysis_worker(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(imd_launcher, "app_dir", lambda: tmp_path)
    monkeypatch.setattr(imd_launcher, "prepare_runtime", lambda root: None)
    monkeypatch.setattr(audio_analysis, "main", lambda args=None: calls.append(args))
    monkeypatch.setattr(
        imd_launcher.sys,
        "argv",
        ["IMD.exe", "--analysis-worker", "--library", "C:/Music", "--output", "report.json"],
    )

    imd_launcher.main()

    assert calls == [["--library", "C:/Music", "--output", "report.json"]]


def test_check_yt_dlp_update_downloads_new_wheel(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(imd_launcher, "current_yt_dlp_version", lambda: "2025.01.01")
    monkeypatch.setattr(
        imd_launcher,
        "pypi_yt_dlp_payload",
        lambda: {
            "info": {"version": "2026.07.17"},
            "urls": [
                {
                    "packagetype": "bdist_wheel",
                    "filename": "yt_dlp-2026.07.17-py3-none-any.whl",
                    "url": "https://example.test/yt_dlp.whl",
                    "digests": {"sha256": hashlib.sha256(b"wheel").hexdigest()},
                }
            ],
        },
    )

    def fake_download(url, destination, timeout=60, expected_sha256=""):
        calls.append((url, destination.name, expected_sha256))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"wheel")

    monkeypatch.setattr(imd_launcher, "download_file", fake_download)
    monkeypatch.setattr(imd_launcher, "add_yt_dlp_update_to_path", lambda root: None)

    result = imd_launcher.check_yt_dlp_update(tmp_path, force=True)

    assert result["updated"] is True
    assert result["latest_version"] == "2026.07.17"
    assert calls == [
        (
            "https://example.test/yt_dlp.whl",
            "yt_dlp_latest.whl",
            hashlib.sha256(b"wheel").hexdigest(),
        )
    ]
    assert imd_launcher.yt_dlp_wheel_path(tmp_path).read_bytes() == b"wheel"


def test_check_yt_dlp_update_skips_after_daily_check(tmp_path):
    imd_launcher.save_json(
        imd_launcher.yt_dlp_meta_path(tmp_path),
        {"last_check": date.today().isoformat(), "current_version": "2026.07.17"},
    )

    result = imd_launcher.check_yt_dlp_update(tmp_path)

    assert result["checked"] is False
    assert result["reason"] == "already_checked_today"


def test_download_file_rejects_invalid_hash(monkeypatch, tmp_path):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            if getattr(self, "done", False):
                return b""
            self.done = True
            return b"tampered"

    monkeypatch.setattr(imd_launcher.urllib.request, "urlopen", lambda request, timeout: FakeResponse())
    destination = tmp_path / "yt_dlp.whl"

    with pytest.raises(RuntimeError, match="SHA256"):
        imd_launcher.download_file(
            "https://example.test/yt_dlp.whl",
            destination,
            expected_sha256=hashlib.sha256(b"expected").hexdigest(),
        )

    assert not destination.exists()
    assert not destination.with_suffix(".whl.tmp").exists()
