from datetime import date

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
                }
            ],
        },
    )

    def fake_download(url, destination, timeout=60):
        calls.append((url, destination.name))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"wheel")

    monkeypatch.setattr(imd_launcher, "download_file", fake_download)
    monkeypatch.setattr(imd_launcher, "add_yt_dlp_update_to_path", lambda root: None)

    result = imd_launcher.check_yt_dlp_update(tmp_path, force=True)

    assert result["updated"] is True
    assert result["latest_version"] == "2026.07.17"
    assert calls == [("https://example.test/yt_dlp.whl", "yt_dlp_latest.whl")]
    assert imd_launcher.yt_dlp_wheel_path(tmp_path).read_bytes() == b"wheel"


def test_check_yt_dlp_update_skips_after_daily_check(tmp_path):
    imd_launcher.save_json(
        imd_launcher.yt_dlp_meta_path(tmp_path),
        {"last_check": date.today().isoformat(), "current_version": "2026.07.17"},
    )

    result = imd_launcher.check_yt_dlp_update(tmp_path)

    assert result["checked"] is False
    assert result["reason"] == "already_checked_today"
