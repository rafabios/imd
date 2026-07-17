import ast
import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "music_downloader.py"
CONFIG = ROOT / "config.yaml"
SAMPLE_CONFIG = ROOT / "config.sample.yaml"


@pytest.fixture(scope="module")
def app():
    spec = importlib.util.spec_from_file_location("music_downloader", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def sample_config():
    with open(SAMPLE_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _has_path(data, dotted_path):
    cur = data
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def test_every_config_path_used_by_script_exists(config):
    code = SCRIPT.read_text(encoding="utf-8-sig")
    tree = ast.parse(code)
    paths = set()

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"config_str", "config_int", "config_bool", "config_list"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            paths.add(node.args[0].value)

    missing = sorted(path for path in paths if not _has_path(config, path))
    assert missing == []


def test_every_config_path_exists_in_sample_config(sample_config):
    code = SCRIPT.read_text(encoding="utf-8-sig")
    tree = ast.parse(code)
    paths = set()

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"config_str", "config_int", "config_bool", "config_list"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            paths.add(node.args[0].value)

    missing = sorted(path for path in paths if not _has_path(sample_config, path))
    assert missing == []


def test_config_values_are_loaded(app):
    assert app.AUDIO_FORMAT == "mp3"
    assert app.MUSIC_DIR
    assert app.STATE_DIR
    assert app.GOOGLE_SHEET_CSV.startswith("https://docs.google.com/")
    assert app.YTDLP_SEARCH_TERMS
    assert app.YTDLP_PLAYER_CLIENTS == ["android", "web", "ios"]


def test_spotify_url_normalization(app):
    url = "https://open.spotify.com/intl-pt/playlist/4419fmChSKR2qkPFIsFTdg?si=abc"
    assert app.normalize_spotify_url(url) == "https://open.spotify.com/playlist/4419fmChSKR2qkPFIsFTdg"


def test_spotify_parse_tracklist_deep_handles_nested_tracks(app):
    payload = {
        "props": {
            "pageProps": {
                "playlist": {
                    "name": "My Playlist",
                    "items": [
                        {
                            "track": {
                                "name": "Song One",
                                "artists": [{"name": "Artist One"}],
                                "album": {"name": "Album One"},
                            }
                        }
                    ],
                }
            }
        }
    }

    result = app.spotify_parse_tracklist_deep(payload)

    assert result["tracks"] == [{"artist": "Artist One", "title": "Song One", "album": "Album One"}]


def test_search_queries_use_config_template(app):
    queries = app.build_search_queries("Artist", "Track")
    assert queries[0] == "Artist Track extended"
    assert "Artist Track official audio" in queries
    assert len(queries) == len(set(queries))


def test_ytdlp_opts_respect_config(app):
    opts = app.yt_dlp_opts("C:/tmp", "Artist - Track")
    assert opts["format"] == app.YTDLP_FORMAT
    assert opts["extractor_retries"] == app.YTDLP_EXTRACTOR_RETRIES
    assert opts["extractor_args"]["youtube"]["player_client"] == app.YTDLP_PLAYER_CLIENTS
    assert opts["remote_components"] == app.YTDLP_REMOTE_COMPONENTS
    assert "cookiesfrombrowser" not in opts


def test_choose_youtube_url_prefers_title_and_artist(app):
    class FakeYDL:
        def extract_info(self, url, download=False):
            assert url.startswith("ytsearch")
            assert download is False
            return {
                "entries": [
                    {"webpage_url": "https://youtu.be/bad", "title": "Other song", "uploader": "Someone"},
                    {"webpage_url": "https://youtu.be/good", "title": "Track official audio", "uploader": "Artist"},
                ]
            }

    assert app.choose_youtube_url(FakeYDL(), "Artist Track official audio", "Artist", "Track") == "https://youtu.be/good"


def test_find_downloaded_file_prefers_configured_extension(app, tmp_path):
    (tmp_path / "Artist - Track.mp4").write_bytes(b"video")
    (tmp_path / "Artist - Track.mp3").write_bytes(b"audio")

    found = app.find_downloaded_file(str(tmp_path), "Artist - Track", preferred_ext=".mp3")

    assert Path(found).name == "Artist - Track.mp3"


def test_dry_run_does_not_download_or_create_history(app, tmp_path):
    hist = set()
    status, out = app.run_youtube_track(
        "Artist",
        "Track",
        "Genre",
        hist,
        target_folder=str(tmp_path / "music"),
        dry_run=True,
    )
    assert status == "dry_run"
    assert out is None
    assert hist == set()
    assert not (tmp_path / "music").exists()


def test_conversion_destination_path(app):
    assert app.conversion_destination_path("C:/Music/Track.m4a", "mp3") == "C:\\Music\\Track.mp3"


def test_conversion_dry_run_does_not_create_or_delete_files(app, tmp_path):
    source = tmp_path / "song.m4a"
    source.write_bytes(b"fake")

    status = app.convert_audio_file(
        str(source),
        "mp3",
        dry_run=True,
        delete_source=True,
        verbose=False,
    )

    assert status == "dry_run"
    assert source.exists()
    assert not (tmp_path / "song.mp3").exists()


def test_run_conversion_mode_dry_run(app, monkeypatch, tmp_path):
    source = tmp_path / "song.m4a"
    source.write_bytes(b"fake")

    monkeypatch.setattr(app, "CONVERSION_ENABLE", True)
    monkeypatch.setattr(app, "CONVERSION_MUSIC_DIR", str(tmp_path))
    monkeypatch.setattr(app, "CONVERSION_SOURCE_FORMAT", "m4a")
    monkeypatch.setattr(app, "CONVERSION_DESTINATION_FORMAT", "mp3")
    monkeypatch.setattr(app, "CONVERSION_DRY_RUN", True)
    monkeypatch.setattr(app, "CONVERSION_DELETE_SOURCE", True)
    monkeypatch.setattr(app, "CONVERSION_VERBOSE", False)
    monkeypatch.setattr(app.shutil, "which", lambda name: "ffmpeg")

    stats = app.run_conversion_mode()

    assert stats["found"] == 1
    assert stats["dry_run"] == 1
    assert stats["converted"] == 0
    assert source.exists()


def test_run_conversion_mode_parallel(app, monkeypatch, tmp_path):
    sources = [tmp_path / f"song-{i}.mp4" for i in range(3)]
    for source in sources:
        source.write_bytes(b"fake")

    calls = []

    def fake_convert(source_path, destination_format, dry_run, delete_source, verbose):
        calls.append(Path(source_path).name)
        return "converted"

    monkeypatch.setattr(app, "CONVERSION_ENABLE", True)
    monkeypatch.setattr(app, "CONVERSION_MUSIC_DIR", str(tmp_path))
    monkeypatch.setattr(app, "CONVERSION_SOURCE_FORMAT", "mp4")
    monkeypatch.setattr(app, "CONVERSION_DESTINATION_FORMAT", "mp3")
    monkeypatch.setattr(app, "CONVERSION_DRY_RUN", False)
    monkeypatch.setattr(app, "CONVERSION_DELETE_SOURCE", True)
    monkeypatch.setattr(app, "CONVERSION_VERBOSE", False)
    monkeypatch.setattr(app, "CONVERSION_WORKERS", 2)
    monkeypatch.setattr(app.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(app, "convert_audio_file", fake_convert)

    stats = app.run_conversion_mode()

    assert stats["found"] == 3
    assert stats["converted"] == 3
    assert stats["failed"] == 0
    assert sorted(calls) == [source.name for source in sources]


def test_track_match_keys_include_title_and_first_artist(app):
    keys = app.track_match_keys("Freakaholics, Vegas (Brazil), Dang3r", "Surto Remix")
    assert "TITLE:surto remix" in keys
    assert "freakaholics|surto remix" in keys


def test_validate_config_accepts_current_config(app):
    app.validate_config()


def test_main_processes_only_row_with_mocks(app, monkeypatch):
    df = pd.DataFrame(
        [
            {"Artista": "A1", "Musica": "T1", "(opcional) Tag/Genero": "G1"},
            {"Artista": "A2", "Musica": "T2", "(opcional) Tag/Genero": "G2"},
        ]
    )
    calls = []

    def fake_run_youtube_track(artist, title, genero, hist, dry_run=False, **kwargs):
        calls.append((artist, title, genero, dry_run))
        return "downloaded", "C:/tmp/A2 - T2.mp3"

    monkeypatch.setattr(app.pd, "read_csv", lambda _: df)
    monkeypatch.setattr(app, "load_history", lambda: set())
    monkeypatch.setattr(app, "save_baixados", lambda items: None)
    monkeypatch.setattr(app, "save_history", lambda hist: None)
    monkeypatch.setattr(app, "tag_downloaded_items", lambda items, only_fill_missing=True: None)
    monkeypatch.setattr(app, "run_youtube_track", fake_run_youtube_track)
    monkeypatch.setattr(app.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(app, "CONVERSION_ONLY", False)
    monkeypatch.setattr(sys, "argv", ["music_downloader.py", "--only-row", "2"])

    app.main()

    assert calls == [("A2", "T2", "G2", False)]


def test_main_processes_only_url_with_mocks(app, monkeypatch):
    calls = []

    def fake_run_spotify_playlist(url, genero, hist, baixados, downloaded_items, reescan_list=False, dry_run=False):
        calls.append((url, genero, reescan_list, dry_run))
        return {"collections": 1, "playlists": 1, "new": 0}

    monkeypatch.setattr(app.pd, "read_csv", lambda _: pd.DataFrame())
    monkeypatch.setattr(app, "load_history", lambda: set())
    monkeypatch.setattr(app, "save_baixados", lambda items: None)
    monkeypatch.setattr(app, "save_history", lambda hist: None)
    monkeypatch.setattr(app, "run_spotify_playlist", fake_run_spotify_playlist)
    monkeypatch.setattr(app.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(app, "CONVERSION_ONLY", False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["music_downloader.py", "--only-url", "https://open.spotify.com/playlist/abc", "--dry-run", "--no-reescan-list"],
    )

    app.main()

    assert calls == [("https://open.spotify.com/playlist/abc", "", False, True)]


def test_main_processes_input_file_with_mocks(app, monkeypatch):
    df = pd.DataFrame([{"Artista": "Imported Artist", "Musica": "Imported Track", "(opcional) Tag/Genero": "Imported"}])
    calls = []
    read_paths = []

    def fake_read_csv(path):
        read_paths.append(path)
        return df

    def fake_run_youtube_track(artist, title, genero, hist, dry_run=False, **kwargs):
        calls.append((artist, title, genero, dry_run))
        return "dry_run", None

    monkeypatch.setattr(app.pd, "read_csv", fake_read_csv)
    monkeypatch.setattr(app, "load_history", lambda: set())
    monkeypatch.setattr(app, "save_baixados", lambda items: None)
    monkeypatch.setattr(app, "save_history", lambda hist: None)
    monkeypatch.setattr(app, "run_youtube_track", fake_run_youtube_track)
    monkeypatch.setattr(app.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(app, "CONVERSION_ONLY", False)
    monkeypatch.setattr(sys, "argv", ["music_downloader.py", "--input-file", "C:/tmp/import.csv", "--dry-run"])

    app.main()

    assert read_paths == ["C:/tmp/import.csv"]
    assert calls == [("Imported Artist", "Imported Track", "Imported", True)]


def test_main_conversion_only_does_not_read_sheet(app, monkeypatch):
    called = []

    monkeypatch.setattr(app, "run_conversion_mode", lambda: called.append("conversion"))
    monkeypatch.setattr(app.pd, "read_csv", lambda _: pytest.fail("read_csv should not run in conversion_only"))
    monkeypatch.setattr(sys, "argv", ["music_downloader.py", "--conversion-only"])

    app.main()

    assert called == ["conversion"]
