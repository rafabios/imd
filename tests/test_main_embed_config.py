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


@pytest.fixture(autouse=True)
def avoid_machine_specific_runtime_directories(app, monkeypatch):
    monkeypatch.setattr(app, "ensure_runtime_dirs", lambda: None)


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
    assert app.YTDLP_CANDIDATE_LIMIT >= app.YTDLP_SEARCH_RESULTS
    assert app.YTDLP_SEARCH_QUERY_LIMIT >= 1
    assert app.YTDLP_DOWNLOAD_ATTEMPTS >= 1
    assert app.YTDLP_PREFER_OFFICIAL is True
    assert app.YTDLP_MIN_SOURCE_BITRATE_KBPS >= 96
    assert app.YTDLP_SPECTRAL_CHECK is True
    assert app.YTDLP_SPECTRAL_CUTOFF_HZ >= 16000


def test_spotify_url_normalization(app):
    url = "https://open.spotify.com/intl-pt/playlist/4419fmChSKR2qkPFIsFTdg?si=abc"
    assert app.normalize_spotify_url(url) == "https://open.spotify.com/playlist/4419fmChSKR2qkPFIsFTdg"


def test_safe_name_handles_windows_reserved_and_long_names(app):
    assert app.safe_name("CON") == "_CON"
    assert app.safe_name("LPT1.mix") == "_LPT1.mix"
    long_name = "musica" * 80
    cleaned = app.safe_name(long_name)
    assert len(cleaned) <= 160
    assert cleaned == app.safe_name(long_name)


def test_spotify_http_uses_certifi_ca_bundle(app, monkeypatch):
    captured = {}
    monkeypatch.setattr(app, "DISABLE_SSL_VERIFY", False)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"<html>ok</html>"

    def fake_urlopen(request, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return FakeResponse()

    monkeypatch.setattr(app.urllib.request, "urlopen", fake_urlopen)

    result = app.spotify_embed_http_get_text("https://open.spotify.com/embed/playlist/abc", timeout=7)

    assert result == "<html>ok</html>"
    assert captured["timeout"] == 7
    assert isinstance(captured["context"], app.ssl.SSLContext)
    assert captured["context"].verify_mode == app.ssl.CERT_REQUIRED


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


def test_spotify_embed_fetches_given_playlist_without_auth(app, monkeypatch):
    requested = []
    payload = {
        "props": {
            "pageProps": {
                "state": {
                    "data": {
                        "entity": {
                            "name": "This Is Vegas (Brazil)",
                            "uri": "spotify:playlist:37i9dQZF1DZ06evO3g6rlh",
                            "trackList": [
                                {"title": "Wana", "subtitle": "Omiki,\u00a0Vegas (Brazil)"},
                                {"title": "Butterfly", "subtitle": "Vegas (Brazil)"},
                            ],
                        }
                    }
                }
            }
        }
    }
    html_text = (
        "<html><head><title>This Is Vegas (Brazil)</title></head><body>"
        f"<script id=\"__NEXT_DATA__\" type=\"application/json\">{app.html.escape(app.json.dumps(payload))}</script>"
        "</body></html>"
    )

    def fake_get(url, timeout=20):
        requested.append(url)
        return html_text

    monkeypatch.setattr(app, "spotify_embed_http_get_text", fake_get)
    monkeypatch.setattr(app, "load_embed_cache", lambda: {})
    monkeypatch.setattr(app, "save_embed_cache", lambda data: None)

    result = app.spotify_embed_fetch_collection(
        "https://open.spotify.com/playlist/37i9dQZF1DZ06evO3g6rlh?si=os5Rkcf6Qg2zQfDcpkTjMw",
        force_refresh=True,
        write_cache=False,
    )

    assert requested == ["https://open.spotify.com/embed/playlist/37i9dQZF1DZ06evO3g6rlh"]
    assert result["entity_type"] == "playlist"
    assert result["name"] == "This Is Vegas (Brazil)"
    assert result["tracks"] == [
        {"artist": "Omiki, Vegas (Brazil)", "title": "Wana", "album": ""},
        {"artist": "Vegas (Brazil)", "title": "Butterfly", "album": ""},
    ]


def test_spotify_embed_fetches_given_artist_without_auth(app, monkeypatch):
    requested = []
    html_text = """
    <html>
      <head><title>Earthspace | Spotify</title></head>
      <body>
        <h3>Afterlife</h3><div>ignore</div><h4>Earthspace,&nbsp;Ital</h4>
        <h3>Freaking Out</h3><div>ignore</div><h4>Earthspace</h4>
      </body>
    </html>
    """

    def fake_get(url, timeout=20):
        requested.append(url)
        return html_text

    monkeypatch.setattr(app, "spotify_embed_http_get_text", fake_get)
    monkeypatch.setattr(app, "load_embed_cache", lambda: {})
    monkeypatch.setattr(app, "save_embed_cache", lambda data: None)

    result = app.spotify_embed_fetch_collection(
        "https://open.spotify.com/intl-pt/artist/6yShdcbFZ0424zEvbm22yY?si=xA4igCeKT4OP7Q3aWwAhkw",
        force_refresh=True,
        write_cache=False,
    )

    assert requested == ["https://open.spotify.com/embed/artist/6yShdcbFZ0424zEvbm22yY"]
    assert result["entity_type"] == "artist"
    assert result["name"] == "Earthspace"
    assert result["tracks"] == [
        {"artist": "Earthspace, Ital", "title": "Afterlife", "album": ""},
        {"artist": "Earthspace", "title": "Freaking Out", "album": ""},
    ]


def test_cached_spotify_playlist_flags_possible_embed_limit(app, monkeypatch):
    url = "https://open.spotify.com/playlist/abc"
    tracks = [{"artist": "A", "title": f"T{i}"} for i in range(50)]
    monkeypatch.setattr(app, "load_embed_cache", lambda: {url: {"tracks": tracks, "count": 50}})
    monkeypatch.setattr(
        app,
        "spotify_embed_http_get_text",
        lambda *args, **kwargs: pytest.fail("cache deveria evitar HTTP"),
    )

    result = app.spotify_embed_fetch_collection(url)

    assert result["partial_possible"] is True


def test_search_queries_use_config_template(app):
    queries = app.build_search_queries("Artist", "Track")
    assert queries[0] == "Artist Track official audio"
    assert "Artist Track official audio" in queries
    assert "Artist Track audio" in queries
    assert "Artist Track extended" not in queries
    assert len(queries) == len(set(queries))


def test_search_queries_prioritize_variant_explicitly_requested_in_title(app):
    queries = app.build_search_queries("Artist", "Track Extended Mix")

    assert queries[0] == "Artist Track Extended Mix extended"


def test_ytdlp_opts_respect_config(app):
    opts = app.yt_dlp_opts("C:/tmp", "Artist - Track")
    assert opts["format"] == app.YTDLP_FORMAT
    assert opts["extractor_retries"] == app.YTDLP_EXTRACTOR_RETRIES
    assert opts["extractor_args"]["youtube"]["player_client"] == app.YTDLP_PLAYER_CLIENTS
    assert opts["remote_components"] == app.YTDLP_REMOTE_COMPONENTS
    assert opts["progress_hooks"] == [app.youtube_source_progress_hook]
    assert opts["extract_flat"] == "in_playlist"
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


def test_choose_youtube_candidates_prefers_official_source_over_unrequested_extended_upload(app, monkeypatch):
    monkeypatch.setattr(app, "YTDLP_SEARCH_RESULTS", 2)
    monkeypatch.setattr(app, "YTDLP_CANDIDATE_LIMIT", 5)
    monkeypatch.setattr(app, "YTDLP_PREFER_OFFICIAL", True)

    unofficial = {
        "webpage_url": "https://youtu.be/extended",
        "title": "The Prodigy - Breathy Extended Mix",
        "uploader": "Dance Uploads",
        "duration": 648,
        "view_count": 1000000,
        "formats": [
            {"format_id": "251", "acodec": "opus", "vcodec": "none", "abr": 160, "asr": 48000},
        ],
    }
    official = {
        "webpage_url": "https://youtu.be/official",
        "title": "The Prodigy - Breathe (Official Audio)",
        "uploader": "The Prodigy",
        "channel": "The Prodigy",
        "channel_is_verified": True,
        "duration": 336,
        "view_count": 500000,
        "formats": [
            {"format_id": "140", "acodec": "mp4a.40.2", "vcodec": "none", "abr": 129, "asr": 44100},
        ],
    }

    class FakeYDL:
        def extract_info(self, url, download=False):
            assert download is False
            return {"entries": [unofficial, official]}

    candidates = app.choose_youtube_candidates(
        FakeYDL(),
        ["The Prodigy Breathy official audio", "The Prodigy Breathy extended"],
        "The Prodigy",
        "Breathy",
    )

    assert candidates[0]["webpage_url"] == "https://youtu.be/official"
    assert candidates[0]["_imd_score"] > candidates[1]["_imd_score"]


def test_explicit_extended_title_is_not_penalized(app, monkeypatch):
    monkeypatch.setattr(app, "YTDLP_PREFER_OFFICIAL", False)
    entry = {"title": "Artist - Track Extended Mix", "uploader": "Artist"}

    requested_score = app.score_youtube_entry(entry, "Artist", "Track Extended Mix")
    generic_score = app.score_youtube_entry(entry, "Artist", "Track")

    assert requested_score > generic_score


def test_variant_markers_use_word_boundaries(app):
    assert app._youtube_variant_penalty("oliver heldens track", "Track") == 0
    assert app._youtube_variant_penalty("artist track live", "Track") == 45


def test_missing_channel_does_not_receive_artist_channel_bonus(app, monkeypatch):
    monkeypatch.setattr(app, "YTDLP_PREFER_OFFICIAL", True)

    assert app._youtube_official_score({"title": "Track"}, "Artist") == 0


def test_youtube_source_description_reports_real_stream_quality(app):
    entry = {
        "formats": [
            {"format_id": "140", "acodec": "mp4a.40.2", "vcodec": "none", "abr": 129, "asr": 44100},
            {"format_id": "251", "acodec": "opus", "vcodec": "none", "abr": 157, "asr": 48000},
        ]
    }

    assert app.best_youtube_audio_format(entry)["format_id"] == "251"
    assert app.youtube_audio_bitrate_kbps(entry) == 157
    assert app.youtube_source_description(entry) == "formato 251 | opus | ~157 kbps | 48 kHz"


def test_youtube_progress_hook_distinguishes_source_from_mp3_output(app, monkeypatch):
    messages = []
    monkeypatch.setattr(app, "AUDIO_FORMAT", "mp3")
    monkeypatch.setattr(app, "QUALITY_AUDIO", "320")
    monkeypatch.setattr(app, "log", messages.append)

    app.youtube_source_progress_hook(
        {
            "status": "finished",
            "info_dict": {
                "format_id": "251",
                "ext": "webm",
                "acodec": "opus",
                "vcodec": "none",
                "abr": 157,
                "asr": 48000,
            },
        }
    )

    assert messages[0] == "Fonte baixada do YouTube: formato 251 | opus | ~157 kbps | 48 kHz"
    assert "fonte ~157 kbps -> MP3 320 kbps" in messages[1]
    assert "nao cria qualidade" in messages[1]


def test_youtube_progress_hook_ignores_non_finished_events(app, monkeypatch):
    messages = []
    monkeypatch.setattr(app, "log", messages.append)

    app.youtube_source_progress_hook({"status": "downloading", "info_dict": {"abr": 157}})

    assert messages == []


def test_spectral_profile_detects_hard_16khz_cutoff(app, monkeypatch):
    monkeypatch.setattr(app, "YTDLP_SPECTRAL_CUTOFF_HZ", 17000)
    monkeypatch.setattr(app, "YTDLP_SPECTRAL_DROP_DB", 20)
    frequencies = app.np.linspace(0, 22050, 2049)
    healthy_magnitude = 1.0 / (1.0 + frequencies / 20000.0)
    lowpass_magnitude = app.np.where(frequencies <= 16000, 1.0, 0.00001)

    healthy = app.evaluate_spectral_profile(frequencies, healthy_magnitude)
    lowpass = app.evaluate_spectral_profile(frequencies, lowpass_magnitude)

    assert healthy["available"] is True
    assert healthy["suspicious"] is False
    assert healthy["cutoff_hz"] >= 20000
    assert lowpass["available"] is True
    assert lowpass["suspicious"] is True
    assert 15700 <= lowpass["cutoff_hz"] <= 16100
    assert lowpass["drop_db"] <= -80


def test_candidates_below_minimum_bitrate_are_ranked_after_acceptable_sources(app, monkeypatch):
    monkeypatch.setattr(app, "YTDLP_MIN_SOURCE_BITRATE_KBPS", 120)
    low_official = {
        "webpage_url": "https://youtu.be/low",
        "title": "Artist - Track (Official Audio)",
        "uploader": "Artist - Topic",
        "formats": [{"format_id": "low", "acodec": "aac", "vcodec": "none", "abr": 64}],
    }
    acceptable = {
        "webpage_url": "https://youtu.be/acceptable",
        "title": "Artist - Track",
        "uploader": "Artist",
        "formats": [{"format_id": "ok", "acodec": "aac", "vcodec": "none", "abr": 128}],
    }

    class FakeYDL:
        def extract_info(self, url, download=False):
            return {"entries": [low_official, acceptable]}

    candidates = app.choose_youtube_candidates(FakeYDL(), ["Artist Track"], "Artist", "Track")

    assert candidates[0]["webpage_url"] == "https://youtu.be/acceptable"
    assert app.youtube_source_quality_tier(candidates[0]) == 2
    assert app.youtube_source_quality_tier(candidates[1]) == 0


def test_candidate_format_inspection_hydrates_flat_search_results(app, monkeypatch):
    monkeypatch.setattr(app, "YTDLP_MIN_SOURCE_BITRATE_KBPS", 120)
    direct_calls = []

    class FakeYDL:
        def extract_info(self, url, download=False):
            if url.startswith("ytsearch"):
                return {
                    "entries": [
                        {"webpage_url": "https://youtu.be/one", "title": "Artist Track", "uploader": "Artist"},
                        {"webpage_url": "https://youtu.be/two", "title": "Artist Track", "uploader": "Artist"},
                    ]
                }
            direct_calls.append(url)
            bitrate = 128 if url.endswith("one") else 160
            return {
                "webpage_url": url,
                "title": "Artist Track",
                "uploader": "Artist",
                "formats": [{"format_id": url[-3:], "acodec": "opus", "vcodec": "none", "abr": bitrate}],
            }

    candidates = app.choose_youtube_candidates(
        FakeYDL(), ["Artist Track"], "Artist", "Track", inspect_formats=True
    )

    assert direct_calls == ["https://youtu.be/one", "https://youtu.be/two"]
    assert candidates[0]["webpage_url"] == "https://youtu.be/two"
    assert app.youtube_audio_bitrate_kbps(candidates[0]) == 160


def test_candidate_search_continues_when_one_query_fails(app):
    class FakeYDL:
        def extract_info(self, url, download=False):
            if "broken query" in url:
                raise RuntimeError("temporary search failure")
            return {
                "entries": [
                    {"webpage_url": "https://youtu.be/good", "title": "Artist Track", "uploader": "Artist"}
                ]
            }

    candidates = app.choose_youtube_candidates(
        FakeYDL(), ["broken query", "Artist Track official audio"], "Artist", "Track"
    )

    assert [item["webpage_url"] for item in candidates] == ["https://youtu.be/good"]


def test_run_youtube_track_falls_back_to_next_ranked_candidate(app, monkeypatch, tmp_path):
    attempts = []
    messages = []
    candidates = [
        {"webpage_url": "https://youtu.be/first", "title": "Artist Track Official", "uploader": "Artist"},
        {"webpage_url": "https://youtu.be/second", "title": "Artist Track", "uploader": "Artist"},
    ]

    class FakeYDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            attempts.append(urls[0])
            if urls[0].endswith("first"):
                return 1
            (tmp_path / "Artist - Track.mp3").write_bytes(b"mp3")
            return 0

    monkeypatch.setattr(app, "YTDLP_DOWNLOAD_ATTEMPTS", 2)
    monkeypatch.setattr(app, "YTDLP_COOKIES_FROM_BROWSER", "")
    monkeypatch.setattr(app, "YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN", False)
    monkeypatch.setattr(app, "AUDIO_FORMAT", "mp3")
    monkeypatch.setattr(app, "DETECT_BPM", False)
    monkeypatch.setattr(app, "build_search_queries", lambda artist, title: ["Artist Track"])
    monkeypatch.setattr(app, "choose_youtube_candidates", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(app, "yt_dlp_opts", lambda *args, **kwargs: {})
    monkeypatch.setattr(app.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(app, "log", messages.append)
    monkeypatch.setattr(app, "log_error", messages.append)
    history = set()

    status, path = app.run_youtube_track(
        "Artist", "Track", "Genre", history, target_folder=str(tmp_path), use_history=False
    )

    assert status == "downloaded"
    assert path == str(tmp_path / "Artist - Track.mp3")
    assert attempts == ["https://youtu.be/first", "https://youtu.be/second"]
    assert any("YouTube selecionado: https://youtu.be/second" in message for message in messages)
    assert app.track_id("Artist", "Track", "Genre") in history


def test_run_youtube_track_retries_after_suspicious_spectral_cutoff(app, monkeypatch, tmp_path):
    attempts = []
    messages = []
    candidates = [
        {"webpage_url": "https://youtu.be/lowpass", "title": "Artist Track", "uploader": "Artist"},
        {"webpage_url": "https://youtu.be/full-spectrum", "title": "Artist Track", "uploader": "Artist"},
    ]

    class FakeYDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            attempts.append(urls[0])
            content = b"lowpass" if urls[0].endswith("lowpass") else b"full-spectrum"
            (tmp_path / "Artist - Track.mp3").write_bytes(content)
            return 0

    def fake_spectrum(path):
        if Path(path).read_bytes() == b"lowpass":
            return {"available": True, "suspicious": True, "cutoff_hz": 15900, "drop_db": -45.0}
        return {"available": True, "suspicious": False, "cutoff_hz": 20100, "drop_db": -4.0}

    monkeypatch.setattr(app, "YTDLP_DOWNLOAD_ATTEMPTS", 2)
    monkeypatch.setattr(app, "YTDLP_COOKIES_FROM_BROWSER", "")
    monkeypatch.setattr(app, "YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN", False)
    monkeypatch.setattr(app, "AUDIO_FORMAT", "mp3")
    monkeypatch.setattr(app, "DETECT_BPM", False)
    monkeypatch.setattr(app, "build_search_queries", lambda artist, title: ["Artist Track"])
    monkeypatch.setattr(app, "choose_youtube_candidates", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(app, "inspect_downloaded_spectrum", fake_spectrum)
    monkeypatch.setattr(app, "yt_dlp_opts", lambda *args, **kwargs: {})
    monkeypatch.setattr(app.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(app, "log", messages.append)
    monkeypatch.setattr(app, "log_error", messages.append)

    status, path = app.run_youtube_track(
        "Artist", "Track", "Genre", set(), target_folder=str(tmp_path), use_history=False
    )

    assert status == "downloaded"
    assert Path(path).read_bytes() == b"full-spectrum"
    assert attempts == ["https://youtu.be/lowpass", "https://youtu.be/full-spectrum"]
    assert any("Corte espectral suspeito" in message for message in messages)
    assert any("proximo candidato" in message for message in messages)
    assert not list(tmp_path.glob(".imd-quality-*"))


def test_all_suspicious_sources_keep_best_spectral_fallback(app, monkeypatch, tmp_path):
    candidates = [
        {"webpage_url": "https://youtu.be/better", "title": "Artist Track", "uploader": "Artist"},
        {"webpage_url": "https://youtu.be/worse", "title": "Artist Track", "uploader": "Artist"},
    ]

    class FakeYDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def download(self, urls):
            (tmp_path / "Artist - Track.mp3").write_bytes(b"better" if urls[0].endswith("better") else b"worse")
            return 0

    def fake_spectrum(path):
        better = Path(path).read_bytes() == b"better"
        return {
            "available": True,
            "suspicious": True,
            "cutoff_hz": 16000 if better else 15000,
            "drop_db": -40.0 if better else -35.0,
        }

    monkeypatch.setattr(app, "YTDLP_DOWNLOAD_ATTEMPTS", 2)
    monkeypatch.setattr(app, "YTDLP_COOKIES_FROM_BROWSER", "")
    monkeypatch.setattr(app, "YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN", False)
    monkeypatch.setattr(app, "AUDIO_FORMAT", "mp3")
    monkeypatch.setattr(app, "DETECT_BPM", False)
    monkeypatch.setattr(app, "build_search_queries", lambda artist, title: ["Artist Track"])
    monkeypatch.setattr(app, "choose_youtube_candidates", lambda *args, **kwargs: candidates)
    monkeypatch.setattr(app, "inspect_downloaded_spectrum", fake_spectrum)
    monkeypatch.setattr(app, "yt_dlp_opts", lambda *args, **kwargs: {})
    monkeypatch.setattr(app.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(app, "log", lambda message: None)
    monkeypatch.setattr(app, "log_error", lambda message: None)

    status, path = app.run_youtube_track(
        "Artist", "Track", "Genre", set(), target_folder=str(tmp_path), use_history=False
    )

    assert status == "downloaded"
    assert Path(path).read_bytes() == b"better"
    assert not list(tmp_path.glob(".imd-quality-*"))


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


def test_bundled_ffmpeg_uses_native_binary_names_on_macos(app, monkeypatch, tmp_path):
    ffmpeg_dir = tmp_path / "vendor" / "ffmpeg"
    ffmpeg_dir.mkdir(parents=True)
    (ffmpeg_dir / "ffmpeg").write_bytes(b"binary")
    (ffmpeg_dir / "ffprobe").write_bytes(b"binary")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app.sys, "platform", "darwin")

    assert app.bundled_ffmpeg_dir() == str(ffmpeg_dir)


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


def test_main_processes_row_numbers_and_ranges_with_mocks(app, monkeypatch):
    df = pd.DataFrame(
        [
            {"Artista": f"A{number}", "Musica": f"T{number}", "(opcional) Tag/Genero": f"G{number}"}
            for number in range(1, 8)
        ]
    )
    calls = []

    def fake_run_youtube_track(artist, title, genero, hist, dry_run=False, **kwargs):
        calls.append((artist, title, genero))
        return "downloaded", f"C:/tmp/{artist} - {title}.mp3"

    monkeypatch.setattr(app.pd, "read_csv", lambda _: df)
    monkeypatch.setattr(app, "load_history", lambda: set())
    monkeypatch.setattr(app, "save_baixados", lambda items: None)
    monkeypatch.setattr(app, "save_history", lambda hist: None)
    monkeypatch.setattr(app, "tag_downloaded_items", lambda items, only_fill_missing=True: None)
    monkeypatch.setattr(app, "run_youtube_track", fake_run_youtube_track)
    monkeypatch.setattr(app.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(app, "CONVERSION_ONLY", False)
    monkeypatch.setattr(sys, "argv", ["music_downloader.py", "--row-selection", "2,4-5,7"])

    app.main()

    assert calls == [
        ("A2", "T2", "G2"),
        ("A4", "T4", "G4"),
        ("A5", "T5", "G5"),
        ("A7", "T7", "G7"),
    ]


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
