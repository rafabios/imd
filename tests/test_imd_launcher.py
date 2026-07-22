from datetime import date
import hashlib

import pytest

import imd_launcher


def test_version_tuple_orders_yt_dlp_versions():
    assert imd_launcher.version_tuple("2026.07.17") > imd_launcher.version_tuple("2025.12.31")
    assert imd_launcher.version_tuple("2026.7.17") == imd_launcher.version_tuple("2026.07.17")


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
