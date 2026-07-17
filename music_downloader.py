import os
import ssl
import math
import re
import sys
import shutil
import subprocess
import json
import html
import argparse
import base64
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from typing import Set, Optional, List, Dict, Any, Tuple

import pandas as pd
import yaml
import yt_dlp
from tqdm import tqdm

try:
    import librosa
    import numpy as np
except Exception:
    librosa = None
    np = None

try:
    from mutagen.mp4 import MP4
    from mutagen.easyid3 import EasyID3
except Exception:
    MP4 = None
    EasyID3 = None

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise RuntimeError(f"Arquivo de configuracao nao encontrado: {config_path.resolve()}")
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise RuntimeError("config.yaml precisa conter um mapa de configuracao.")
    return data

CONFIG = load_config()

def config_value(path: str, default: Any = None) -> Any:
    cur: Any = CONFIG
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def config_str(path: str, default: str = "") -> str:
    value = config_value(path, default)
    if value is None:
        return ""
    return str(value).strip()

def config_int(path: str, default: int = 0) -> int:
    value = config_value(path, default)
    if value is None or value == "":
        return default
    return int(value)

def config_bool(path: str, default: bool = False) -> bool:
    value = config_value(path, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "sim", "on")

def config_list(path: str, default: Optional[List[str]] = None) -> List[str]:
    value = config_value(path, default or [])
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in str(value).split(",") if x.strip()]

# =========================
# Config
# =========================
MUSIC_DIR = config_str("paths.music_dir", "/data/music")
STATE_DIR = config_str("paths.state_dir", "/data/state")
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

HISTORICO_FILE = os.path.join(STATE_DIR, "historico.txt")
TRACKS_HISTORY_FILE = os.path.join(STATE_DIR, "tracks_history.txt")
SPOTIFY_HISTORY_FILE = os.path.join(STATE_DIR, "spotify_history.txt")
FILES_HISTORY_FILE = os.path.join(STATE_DIR, "files_history.txt")
BAIXADOS_FILE = os.path.join(STATE_DIR, "baixados.txt")
ERROS_FILE = os.path.join(STATE_DIR, "erros.txt")
FAILED_ITEMS_FILE = os.path.join(STATE_DIR, "failed_items.jsonl")
SPOTIFY_EMBED_CACHE_FILE = os.path.join(STATE_DIR, "spotify_embed_cache.json")
SPOTIFY_EMBED_DEBUG_FILE = os.path.join(STATE_DIR, "spotify_embed_last.html")

AUDIO_FORMAT = config_str("audio.format", "m4a").lower()
QUALITY_AUDIO = config_str("audio.quality", "320")

DETECT_BPM = config_bool("audio.detect_bpm", False)
BPM_SECONDS = config_int("audio.bpm_seconds", 20)

EMBED_METADATA = config_bool("audio.embed_metadata", False)
EMBED_THUMBNAIL = config_bool("audio.embed_thumbnail", False)
AUTO_TAG_AFTER_DOWNLOAD = config_bool("audio.auto_tag_after_download", False)
AUTO_TAG_FORCE = config_bool("audio.auto_tag_force", False)

YTDLP_FORMAT = config_str("ytdlp.format", "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio/best")
YTDLP_PLAYER_CLIENT = config_str("ytdlp.player_client", "android")
YTDLP_PLAYER_CLIENTS = config_list("ytdlp.player_clients", [])
YTDLP_CONCURRENT_FRAGMENTS = config_int("ytdlp.concurrent_fragments", 8)
YTDLP_REMOTE_COMPONENTS = config_list("ytdlp.remote_components", ["ejs:github"])
YTDLP_VERBOSE = config_bool("ytdlp.verbose", False)
YTDLP_COOKIES_FROM_BROWSER = config_str("ytdlp.cookies_from_browser", "")
YTDLP_SEARCH_TERMS = config_list("ytdlp.search_terms", ["extended"])
YTDLP_QUERY_TEMPLATE = config_str("ytdlp.query_template", "{artist} {title} {term}")
YTDLP_SEARCH_RESULTS = config_int("ytdlp.search_results", 3)
YTDLP_EXTRACTOR_RETRIES = config_int("ytdlp.extractor_retries", 3)

SPOTIFY_MODE = config_str("spotify.mode", "EMBED").upper()
SPOTIFY_EMBED_TIMEOUT_SECONDS = config_int("spotify.embed_timeout_seconds", 20)
SPOTIFY_ARTIST_MODE = config_str("spotify.artist_mode", "top_tracks").lower()
SPOTIFY_ARTIST_MARKET = config_str("spotify.artist_market", "BR")
SPOTIFY_ARTIST_ALBUM_GROUPS = config_list("spotify.artist_album_groups", ["album", "single"])
SPOTIFY_ARTIST_MAX_ALBUMS = config_int("spotify.artist_max_albums", 0)
SPOTIFY_ARTIST_MAX_TRACKS = config_int("spotify.artist_max_tracks", 0)

GOOGLE_SHEET_CSV = config_str("source.google_sheet_csv", "")
LOG_LEVEL = config_str("execution.log_level", "INFO").upper()
SPOTIFY_CREDENTIALS_FILE = config_str("spotify.credentials_file", "")
SPOTIPY_CLIENT_ID = config_str("spotify.client_id", "")
SPOTIPY_CLIENT_SECRET = config_str("spotify.client_secret", "")
DISABLE_SSL_VERIFY = config_bool("network.disable_ssl_verify", False)
MARK_COLLECTION_DONE_WITH_FAILURES = config_bool("history.mark_collection_done_with_failures", False)
MAX_FAILURES_TO_MARK_DONE = config_int("history.max_failures_to_mark_done", 0)

CONVERSION_ENABLE = config_bool("conversion.enable", False)
CONVERSION_ONLY = config_bool("conversion.conversion_only", False)
CONVERSION_VERBOSE = config_bool("conversion.verbose", True)
CONVERSION_MUSIC_DIR = config_str("conversion.music_dir", MUSIC_DIR)
CONVERSION_SOURCE_FORMAT = config_str("conversion.source_format", "m4a").lower().lstrip(".")
CONVERSION_DESTINATION_FORMAT = config_str("conversion.destination_format", "mp3").lower().lstrip(".")
CONVERSION_DRY_RUN = config_bool("conversion.dry_run", True)
CONVERSION_DELETE_SOURCE = config_bool("conversion.delete_source", False)
CONVERSION_WORKERS = config_int("conversion.workers", 1)
CONVERSION_FFMPEG_THREADS = config_int("conversion.ffmpeg_threads", 1)

def load_credentials_file(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    cred_path = Path(path)
    if not cred_path.is_absolute():
        cred_path = Path.cwd() / cred_path
    if not cred_path.exists():
        return {}
    with open(cred_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}

SPOTIFY_SECRETS = load_credentials_file(SPOTIFY_CREDENTIALS_FILE)
if not SPOTIPY_CLIENT_ID:
    SPOTIPY_CLIENT_ID = str(SPOTIFY_SECRETS.get("client_id") or "").strip()
if not SPOTIPY_CLIENT_SECRET:
    SPOTIPY_CLIENT_SECRET = str(SPOTIFY_SECRETS.get("client_secret") or "").strip()

AUDIO_EXTS = {".mp3", ".m4a", ".mp4", ".flac", ".wav", ".aiff", ".aif"}
YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN = False

if DISABLE_SSL_VERIFY:
    ssl._create_default_https_context = ssl._create_unverified_context

def validate_config() -> None:
    errors = []
    if AUDIO_FORMAT not in ("mp3", "m4a"):
        errors.append("audio.format deve ser 'mp3' ou 'm4a'.")
    if SPOTIFY_MODE not in ("EMBED", "INDEX_ONLY", "YOUTUBE_ONLY", "OFF"):
        errors.append("spotify.mode deve ser EMBED, INDEX_ONLY, YOUTUBE_ONLY ou OFF.")
    if SPOTIFY_ARTIST_MODE not in ("top_tracks", "discography", "albums", "all"):
        errors.append("spotify.artist_mode deve ser top_tracks ou discography.")
    allowed_album_groups = {"album", "single", "appears_on", "compilation"}
    invalid_groups = [x for x in SPOTIFY_ARTIST_ALBUM_GROUPS if x not in allowed_album_groups]
    if invalid_groups:
        errors.append(f"spotify.artist_album_groups contem valores invalidos: {', '.join(invalid_groups)}.")
    if LOG_LEVEL not in ("DEBUG", "INFO", "QUIET"):
        errors.append("execution.log_level deve ser DEBUG, INFO ou QUIET.")
    if "{artist}" not in YTDLP_QUERY_TEMPLATE or "{title}" not in YTDLP_QUERY_TEMPLATE:
        errors.append("ytdlp.query_template precisa conter {artist} e {title}.")
    if not YTDLP_SEARCH_TERMS:
        errors.append("ytdlp.search_terms precisa ter pelo menos um item.")
    if YTDLP_CONCURRENT_FRAGMENTS < 1:
        errors.append("ytdlp.concurrent_fragments precisa ser maior ou igual a 1.")
    if YTDLP_EXTRACTOR_RETRIES < 0:
        errors.append("ytdlp.extractor_retries precisa ser maior ou igual a 0.")
    if YTDLP_SEARCH_RESULTS < 1:
        errors.append("ytdlp.search_results precisa ser maior ou igual a 1.")
    if SPOTIFY_ARTIST_MAX_ALBUMS < 0:
        errors.append("spotify.artist_max_albums deve ser null ou maior/igual a 0.")
    if SPOTIFY_ARTIST_MAX_TRACKS < 0:
        errors.append("spotify.artist_max_tracks deve ser null ou maior/igual a 0.")
    supported_conversion_source_formats = {"mp3", "m4a", "mp4", "flac", "wav", "ogg", "opus", "aac"}
    supported_conversion_destination_formats = {"mp3", "m4a", "flac", "wav", "ogg", "opus", "aac"}
    if CONVERSION_SOURCE_FORMAT not in supported_conversion_source_formats:
        errors.append(f"conversion.source_format invalido: {CONVERSION_SOURCE_FORMAT}.")
    if CONVERSION_DESTINATION_FORMAT not in supported_conversion_destination_formats:
        errors.append(f"conversion.destination_format invalido: {CONVERSION_DESTINATION_FORMAT}.")
    if CONVERSION_SOURCE_FORMAT == CONVERSION_DESTINATION_FORMAT:
        errors.append("conversion.source_format e conversion.destination_format precisam ser diferentes.")
    if CONVERSION_WORKERS < 1:
        errors.append("conversion.workers precisa ser maior ou igual a 1.")
    if CONVERSION_FFMPEG_THREADS < 1:
        errors.append("conversion.ffmpeg_threads precisa ser maior ou igual a 1.")
    if errors:
        raise RuntimeError("Config invalido:\n- " + "\n- ".join(errors))

validate_config()

# =========================
# Utils / Logs
# =========================
def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str) -> None:
    if LOG_LEVEL in ("DEBUG", "INFO"):
        print(msg, flush=True)

def debug(msg: str) -> None:
    if LOG_LEVEL == "DEBUG":
        print(msg, flush=True)

def log_error(msg: str) -> None:
    try:
        with open(ERROS_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts()}] {msg}\n")
    except Exception:
        print(f"[{ts()}] {msg}", flush=True)

def log_failed_item(kind: str, error: str, artist: str = "", title: str = "", genre: str = "", spotify_url: str = "", row_number: Optional[int] = None) -> None:
    item = {
        "timestamp": ts(),
        "kind": kind,
        "row_number": row_number,
        "artist": artist,
        "title": title,
        "genre": genre,
        "spotify_url": spotify_url,
        "error": error,
    }
    try:
        with open(FAILED_ITEMS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    except Exception as e:
        log_error(f"[FAILED_ITEMS] write failed: {e}")

def is_nan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and v.strip().lower() == "nan")

def normalize(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()

def normalize_loose(s: str) -> str:
    s = (s or "").replace("\xa0", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s)
    return " ".join(s.lower().split())

def safe_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    if re.match(r"^-[A-Za-zÀ-ÿ0-9]", s):
        s = s[1:].strip()
    s = s.rstrip(". ").strip()
    return s or "Sem_Nome"

SPOTIFY_ENTITY_TYPES = ("playlist", "artist")

def spotify_detect_entity_type(url: str) -> str:
    url = (url or "").strip().lower()
    if "/artist/" in url:
        return "artist"
    if "/playlist/" in url:
        return "playlist"
    return ""

def is_spotify_url(v: str) -> bool:
    return isinstance(v, str) and "open.spotify.com" in v and any(f"/{t}/" in v for t in SPOTIFY_ENTITY_TYPES)

def normalize_spotify_url(url: str) -> str:
    url = (url or "").strip()
    m = re.search(r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?(?:embed/)?(playlist|artist)/([A-Za-z0-9]+)", url, flags=re.I)
    if not m:
        return url
    return f"https://open.spotify.com/{m.group(1).lower()}/{m.group(2)}"

def spotify_extract_entity_id(url: str, entity_type: Optional[str] = None) -> str:
    url = normalize_spotify_url(url)
    entity_type = entity_type or spotify_detect_entity_type(url)
    if not entity_type:
        return ""
    m = re.search(rf"/{entity_type}/([A-Za-z0-9]+)", url)
    return m.group(1) if m else ""

def spotify_extract_playlist_id(url: str) -> str:
    return spotify_extract_entity_id(url, "playlist")

def spotify_extract_artist_id(url: str) -> str:
    return spotify_extract_entity_id(url, "artist")

def track_id(artist: str, title: str, genero: str) -> str:
    return f"TRACK:{normalize(artist)}|{normalize(title)}|{normalize(genero)}"

def spotify_entity_history_id(url: str) -> str:
    entity_type = spotify_detect_entity_type(url) or "spotify"
    return f"{entity_type.upper()}:{normalize_spotify_url(url)}"

def playlist_id(url: str) -> str:
    return spotify_entity_history_id(url)

def load_history_file(path: str) -> Set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(x.strip() for x in f if x.strip())

def load_history() -> Set[str]:
    hist = set()
    for path in (HISTORICO_FILE, TRACKS_HISTORY_FILE, SPOTIFY_HISTORY_FILE, FILES_HISTORY_FILE):
        hist.update(load_history_file(path))
    return hist

def save_lines_atomic(path: str, lines: List[str]) -> None:
    tmp_file = path + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        for x in lines:
            f.write(x + "\n")
    os.replace(tmp_file, path)

def save_history(hist: Set[str]) -> None:
    sorted_hist = sorted(hist)
    save_lines_atomic(HISTORICO_FILE, sorted_hist)
    save_lines_atomic(TRACKS_HISTORY_FILE, [x for x in sorted_hist if x.startswith("TRACK:")])
    save_lines_atomic(SPOTIFY_HISTORY_FILE, [x for x in sorted_hist if x.startswith(("PLAYLIST:", "ARTIST:"))])
    save_lines_atomic(FILES_HISTORY_FILE, [x for x in sorted_hist if x.startswith("FILE:")])

def save_baixados(lista: List[str]) -> None:
    save_lines_atomic(BAIXADOS_FILE, lista)

def load_embed_cache() -> Dict[str, Any]:
    if not os.path.exists(SPOTIFY_EMBED_CACHE_FILE):
        return {}
    try:
        with open(SPOTIFY_EMBED_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        log_error(f"[SPOTIFY_EMBED_CACHE] load failed: {e}")
        return {}

def save_embed_cache(data: Dict[str, Any]) -> None:
    try:
        with open(SPOTIFY_EMBED_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_error(f"[SPOTIFY_EMBED_CACHE] save failed: {e}")

# =========================
# BPM
# =========================
def detect_bpm(path: str) -> Optional[int]:
    if not librosa or not np:
        return None
    try:
        y, sr = librosa.load(path, sr=22050, mono=True, duration=BPM_SECONDS)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempos = librosa.feature.rhythm.tempo(onset_envelope=onset_env, sr=sr)
        if isinstance(tempos, (list, np.ndarray)) and len(tempos) > 0:
            return int(round(float(tempos[0])))
        return None
    except Exception as e:
        log_error(f"[BPM] {path} :: {e}")
        return None

# =========================
# yt-dlp
# =========================
def yt_dlp_opts(folder: str, base: str, use_browser_cookies: bool = True) -> dict:
    outtmpl = os.path.join(folder, base + ".%(ext)s")
    postprocessors = []

    if AUDIO_FORMAT == "mp3":
        postprocessors.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": QUALITY_AUDIO,
        })

    opts = {
        "format": YTDLP_FORMAT,
        "outtmpl": outtmpl,
        "quiet": not YTDLP_VERBOSE,
        "no_warnings": not YTDLP_VERBOSE,
        "noplaylist": True,
        "ignoreerrors": True,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": YTDLP_EXTRACTOR_RETRIES,
        "concurrent_fragment_downloads": YTDLP_CONCURRENT_FRAGMENTS,
        "extractor_args": {"youtube": {"player_client": YTDLP_PLAYER_CLIENTS or [YTDLP_PLAYER_CLIENT]}},
        "postprocessors": postprocessors,
        "embed_metadata": EMBED_METADATA,
        "add_metadata": EMBED_METADATA,
        "embed_thumbnail": EMBED_THUMBNAIL,
    }

    if use_browser_cookies and not YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN and YTDLP_COOKIES_FROM_BROWSER and YTDLP_COOKIES_FROM_BROWSER.lower() not in ("0", "none", "off", "false", "no"):
        opts["cookiesfrombrowser"] = (YTDLP_COOKIES_FROM_BROWSER,)

    if YTDLP_REMOTE_COMPONENTS:
        opts["remote_components"] = YTDLP_REMOTE_COMPONENTS

    return opts

def find_downloaded_file(folder: str, base: str, preferred_ext: Optional[str] = None) -> Optional[str]:
    if not os.path.exists(folder):
        return None
    preferred_ext = (preferred_ext or "").lower()
    candidates = []
    for f in os.listdir(folder):
        if f.startswith(base + ".") or f.startswith(base + " ("):
            candidates.append(f)
    if not candidates:
        for f in os.listdir(folder):
            if f.startswith(base):
                candidates.append(f)
    if not candidates:
        return None
    candidates.sort(key=lambda x: (0 if preferred_ext and Path(x).suffix.lower() == preferred_ext else 1, len(x), x))
    return os.path.join(folder, candidates[0])

def convert_existing_to_mp3(source_path: str) -> Optional[str]:
    source = Path(source_path)
    destination = str(source.with_suffix(".mp3"))
    if source.suffix.lower() == ".mp3":
        return str(source)
    if os.path.exists(destination):
        return destination
    if not shutil.which("ffmpeg"):
        log_error(f"[YOUTUBE] Nao foi possivel converter para mp3 sem ffmpeg: {source_path}")
        return None
    cmd = ["ffmpeg", "-y", "-i", str(source), "-vn", "-codec:a", "libmp3lame", "-b:a", f"{QUALITY_AUDIO}k", destination]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        log_error(f"[YOUTUBE] ffmpeg falhou ao converter {source_path}: {result.stderr}")
        return None
    log(f"Convertido para mp3: {os.path.basename(destination)}")
    return destination

def build_search_queries(artist: str, title: str) -> List[str]:
    terms = YTDLP_SEARCH_TERMS or [""]
    queries = []
    seen = set()
    for term in terms:
        query = YTDLP_QUERY_TEMPLATE.format(artist=artist, title=title, term=term).strip()
        query = re.sub(r"\s+", " ", query)
        key = normalize_loose(query)
        if query and key not in seen:
            queries.append(query)
            seen.add(key)
    return queries

def score_youtube_entry(entry: Dict[str, Any], artist: str, title: str) -> int:
    text = normalize_loose(" ".join(str(entry.get(k) or "") for k in ("title", "uploader", "channel")))
    artist_key = normalize_loose(artist)
    title_key = normalize_loose(title)
    score = 0
    if title_key and title_key in text:
        score += 100
    for word in title_key.split():
        if len(word) > 2 and word in text:
            score += 8
    first_artist = normalize_loose(re.split(r",|&| feat\\.? | ft\\.? ", artist, maxsplit=1, flags=re.I)[0])
    if first_artist and first_artist in text:
        score += 40
    for word in artist_key.split():
        if len(word) > 2 and word in text:
            score += 4
    duration = entry.get("duration")
    if isinstance(duration, (int, float)) and 90 <= duration <= 900:
        score += 10
    return score

def choose_youtube_url(ydl: yt_dlp.YoutubeDL, query: str, artist: str, title: str) -> Optional[str]:
    search_count = max(1, YTDLP_SEARCH_RESULTS)
    info = ydl.extract_info(f"ytsearch{search_count}:{query}", download=False)
    entries = [x for x in (info or {}).get("entries") or [] if x]
    if not entries:
        return None
    best = max(entries, key=lambda item: score_youtube_entry(item, artist, title))
    return best.get("webpage_url") or best.get("url")

def run_youtube_track(
    artist: str,
    title: str,
    genero: str,
    hist: Set[str],
    target_folder: Optional[str] = None,
    use_history: bool = True,
    dry_run: bool = False,
) -> Tuple[str, Optional[str]]:
    global YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN

    tid = track_id(artist, title, genero)
    if use_history and tid in hist:
        debug(f"Skip by history: {tid}")
        return "skipped_history", None

    folder = target_folder or os.path.join(MUSIC_DIR, safe_name(genero) if genero else "Sem_Genero")
    if not dry_run:
        os.makedirs(folder, exist_ok=True)

    base = safe_name(f"{artist} - {title}")
    preferred_ext = f".{AUDIO_FORMAT}" if AUDIO_FORMAT else None
    existing = find_downloaded_file(folder, base, preferred_ext=preferred_ext)
    if AUDIO_FORMAT == "mp3" and existing and Path(existing).suffix.lower() != ".mp3":
        existing = convert_existing_to_mp3(existing)

    if existing and os.path.exists(existing):
        if not dry_run:
            hist.add(tid)
            hist.add(f"FILE:{os.path.basename(existing)}")
        log(f"⏭️ Já existe no disco: {os.path.basename(existing)}")
        return "skipped_existing", None

    queries = build_search_queries(artist, title)
    if dry_run:
        log(f"DRY-RUN baixaria: {queries[0] if queries else f'{artist} {title}'} -> {folder}")
        return "dry_run", None

    final_path = None
    last_error = ""
    for query in queries:
        cookie_attempts = [not YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN]
        if cookie_attempts[0] and YTDLP_COOKIES_FROM_BROWSER and YTDLP_COOKIES_FROM_BROWSER.lower() not in ("0", "none", "off", "false", "no"):
            cookie_attempts.append(False)

        for use_browser_cookies in cookie_attempts:
            try:
                if not use_browser_cookies:
                    log(f"Tentando sem cookies do navegador: {query}")
                with yt_dlp.YoutubeDL(yt_dlp_opts(folder, base, use_browser_cookies=use_browser_cookies)) as ydl:
                    selected_url = choose_youtube_url(ydl, query, artist, title)
                    if not selected_url:
                        last_error = "no youtube search results"
                        continue
                    log(f"YouTube selecionado: {selected_url}")
                    ydl.download([selected_url])

                    final_path = find_downloaded_file(folder, base, preferred_ext=preferred_ext)
                    if AUDIO_FORMAT == "mp3" and (not final_path or Path(final_path).suffix.lower() != ".mp3"):
                        downloaded_path = find_downloaded_file(folder, base)
                        if downloaded_path:
                            final_path = convert_existing_to_mp3(downloaded_path)
                    if final_path and os.path.exists(final_path):
                        break
                    last_error = "file not found after download"
            except Exception as e:
                last_error = str(e)
                log_error(f"[YOUTUBE] Exception: {query} :: {e}")
                if use_browser_cookies and "cookie" in last_error.lower():
                    YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN = True
                    log("Cookies do navegador falharam; desativando cookies para o restante desta execucao.")

        if final_path and os.path.exists(final_path):
            break

    if not final_path or not os.path.exists(final_path):
        log_error(f"[YOUTUBE] File not found after download: {artist} - {title} :: {last_error}")
        return "failed", None

    try:
        if DETECT_BPM:
            bpm = detect_bpm(final_path)
            if bpm:
                ext = os.path.splitext(final_path)[1]
                new_name = safe_name(f"{base} ({bpm} BPM)") + ext
                new_path = os.path.join(folder, new_name)
                if not os.path.exists(new_path):
                    os.rename(final_path, new_path)
                    final_path = new_path

        hist.add(tid)
        hist.add(f"FILE:{os.path.basename(final_path)}")
        log(f"✅ YouTube OK: {os.path.basename(final_path)}")
        return "downloaded", final_path
    except Exception as e:
        log_error(f"[YOUTUBE] Post-process exception: {query} :: {e}")
        return "failed", None

# =========================
# Spotify via public embed __NEXT_DATA__
# =========================
def spotify_embed_http_get_text(url: str, timeout: int = 20) -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log_error(f"[SPOTIFY_EMBED] HTTP error {url} :: {e}")
        return None

def spotify_extract_next_data(html_text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text, flags=re.S | re.I)
    if not m:
        return None
    raw = html.unescape(m.group(1)).strip()
    try:
        return json.loads(raw)
    except Exception as e:
        log_error(f"[SPOTIFY_EMBED] __NEXT_DATA__ parse failed: {e}")
        return None

def spotify_parse_embed_tracklist(next_data: Dict[str, Any]) -> Dict[str, Any]:
    entity = (((next_data or {}).get("props") or {}).get("pageProps") or {}).get("state", {}).get("data", {}).get("entity", {})
    entity_name = (entity.get("name") or entity.get("title") or "").strip()
    entity_uri = (entity.get("uri") or "").strip()
    tracks_raw = entity.get("trackList") or []

    tracks: List[Dict[str, str]] = []
    seen = set()

    for item in tracks_raw:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        artist = (item.get("subtitle") or item.get("artist") or "").strip()
        if not title or not artist:
            continue
        key = (normalize(artist), normalize(title))
        if key in seen:
            continue
        seen.add(key)
        tracks.append({
            "artist": artist,
            "title": title,
            "album": "",
        })

    return {
        "name": entity_name,
        "uri": entity_uri,
        "tracks": tracks,
        "count": len(tracks),
    }

def spotify_parse_tracklist_deep(next_data: Dict[str, Any]) -> Dict[str, Any]:
    tracks: List[Dict[str, str]] = []
    seen = set()
    entity_name = ""

    def add_track(title: str, artist: str, album: str = "") -> None:
        title = (title or "").strip()
        artist = (artist or "").strip()
        album = (album or "").strip()
        key = (normalize_loose(artist), normalize_loose(title))
        if artist and title and key not in seen:
            seen.add(key)
            tracks.append({"artist": artist, "title": title, "album": album})

    def artist_names(value: Any) -> str:
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    name = (item.get("name") or item.get("title") or "").strip()
                    if name:
                        names.append(name)
                elif isinstance(item, str) and item.strip():
                    names.append(item.strip())
            return ", ".join(names)
        if isinstance(value, str):
            return value.strip()
        return ""

    def walk(value: Any) -> None:
        nonlocal entity_name
        if isinstance(value, dict):
            if not entity_name:
                entity_name = str(value.get("name") or value.get("title") or "").strip()

            title = str(value.get("name") or value.get("title") or "").strip()
            artist = (
                artist_names(value.get("artists"))
                or artist_names(value.get("artist"))
                or str(value.get("subtitle") or "").strip()
            )
            album = ""
            if isinstance(value.get("album"), dict):
                album = str(value["album"].get("name") or value["album"].get("title") or "").strip()
            if title and artist:
                add_track(title, artist, album)

            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(next_data)
    return {
        "name": entity_name,
        "uri": "",
        "tracks": tracks,
        "count": len(tracks),
    }

def spotify_parse_embed_tracklist_from_html(html_text: str) -> Dict[str, Any]:
    clean = html.unescape(html_text or "")
    title_match = re.search(r"<title>(.*?)</title>", clean, flags=re.I | re.S)
    entity_name = ""
    if title_match:
        entity_name = re.sub(r"\s+", " ", title_match.group(1)).strip()
        entity_name = re.sub(r"[·•|].*$", "", entity_name).strip()

    tracks: List[Dict[str, str]] = []
    seen = set()
    pattern = re.compile(
        r"<h3[^>]*>\s*(.*?)\s*</h3>.*?<h4[^>]*>\s*(.*?)\s*</h4>",
        flags=re.I | re.S,
    )

    for m in pattern.finditer(clean):
        title = re.sub(r"<.*?>", "", m.group(1)).strip()
        artist = re.sub(r"<.*?>", "", m.group(2)).strip()
        artist = re.sub(r"^E\s+", "", artist).strip()
        if not title or not artist:
            continue
        key = (normalize(artist), normalize(title))
        if key in seen:
            continue
        seen.add(key)
        tracks.append({"artist": artist, "title": title, "album": ""})

    return {
        "name": entity_name,
        "uri": "",
        "tracks": tracks,
        "count": len(tracks),
    }

def spotify_get_client_token() -> Optional[str]:
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        log_error("[SPOTIFY_API] Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET")
        return None

    creds = f"{SPOTIPY_CLIENT_ID}:{SPOTIPY_CLIENT_SECRET}".encode("utf-8")
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        headers={
            "Authorization": f"Basic {base64.b64encode(creds).decode('ascii')}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "music-downloader/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            return payload.get("access_token")
    except Exception as e:
        log_error(f"[SPOTIFY_API] Token error: {e}")
        return None

def spotify_api_get_json(url: str, token: str) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "music-downloader/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        log_error(f"[SPOTIFY_API] GET failed: {url} :: {e}")
        return None

def spotify_api_fetch_collection(url: str) -> Optional[Dict[str, Any]]:
    norm_url = normalize_spotify_url(url)
    entity_type = spotify_detect_entity_type(norm_url)
    entity_id = spotify_extract_entity_id(norm_url, entity_type)
    if not entity_id or entity_type not in SPOTIFY_ENTITY_TYPES:
        return None

    token = spotify_get_client_token()
    if not token:
        return None

    tracks: List[Dict[str, str]] = []
    name = ""
    seen_tracks = set()

    def add_track(track: Dict[str, Any]) -> None:
        title = (track.get("name") or "").strip()
        artists = track.get("artists") or []
        artist = ", ".join((a.get("name") or "").strip() for a in artists if isinstance(a, dict) and a.get("name"))
        album = ((track.get("album") or {}).get("name") or "").strip()
        key = (normalize_loose(artist), normalize_loose(title))
        if artist and title and key not in seen_tracks:
            seen_tracks.add(key)
            tracks.append({"artist": artist, "title": title, "album": album})

    if entity_type == "playlist":
        meta = spotify_api_get_json(
            f"https://api.spotify.com/v1/playlists/{entity_id}?fields=name,tracks.total",
            token,
        )
        if meta:
            name = (meta.get("name") or "").strip()

        offset = 0
        limit = 100
        while True:
            page = spotify_api_get_json(
                f"https://api.spotify.com/v1/playlists/{entity_id}/tracks"
                f"?limit={limit}&offset={offset}"
                f"&fields=items(track(name,artists(name),album(name))),next,total",
                token,
            )
            if not page:
                break
            for item in page.get("items") or []:
                track = (item or {}).get("track") or {}
                add_track(track)
            if not page.get("next"):
                break
            offset += limit

    elif entity_type == "artist":
        meta = spotify_api_get_json(f"https://api.spotify.com/v1/artists/{entity_id}", token)
        if meta:
            name = (meta.get("name") or "").strip()
        if SPOTIFY_ARTIST_MODE in ("discography", "albums", "all"):
            offset = 0
            limit = 50
            album_ids = []
            while True:
                page = spotify_api_get_json(
                    f"https://api.spotify.com/v1/artists/{entity_id}/albums"
                    f"?include_groups={urllib.parse.quote(','.join(SPOTIFY_ARTIST_ALBUM_GROUPS))}&market={urllib.parse.quote(SPOTIFY_ARTIST_MARKET)}"
                    f"&limit={limit}&offset={offset}",
                    token,
                )
                if not page:
                    break
                for album in page.get("items") or []:
                    album_id = (album or {}).get("id")
                    if album_id and album_id not in album_ids:
                        album_ids.append(album_id)
                        if SPOTIFY_ARTIST_MAX_ALBUMS and len(album_ids) >= SPOTIFY_ARTIST_MAX_ALBUMS:
                            break
                if SPOTIFY_ARTIST_MAX_ALBUMS and len(album_ids) >= SPOTIFY_ARTIST_MAX_ALBUMS:
                    break
                if not page.get("next"):
                    break
                offset += limit

            for album_id in album_ids:
                if SPOTIFY_ARTIST_MAX_TRACKS and len(tracks) >= SPOTIFY_ARTIST_MAX_TRACKS:
                    break
                offset = 0
                while True:
                    page = spotify_api_get_json(
                        f"https://api.spotify.com/v1/albums/{album_id}/tracks"
                        f"?market={urllib.parse.quote(SPOTIFY_ARTIST_MARKET)}&limit=50&offset={offset}",
                        token,
                    )
                    if not page:
                        break
                    for track in page.get("items") or []:
                        add_track(track)
                        if SPOTIFY_ARTIST_MAX_TRACKS and len(tracks) >= SPOTIFY_ARTIST_MAX_TRACKS:
                            break
                    if SPOTIFY_ARTIST_MAX_TRACKS and len(tracks) >= SPOTIFY_ARTIST_MAX_TRACKS:
                        break
                    if not page.get("next"):
                        break
                    offset += 50
        else:
            page = spotify_api_get_json(
                f"https://api.spotify.com/v1/artists/{entity_id}/top-tracks?market={urllib.parse.quote(SPOTIFY_ARTIST_MARKET)}",
                token,
            )
            for track in (page or {}).get("tracks") or []:
                add_track(track)

    if not tracks:
        return None

    return {
        "url": norm_url,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "name": name,
        "uri": "",
        "tracks": tracks,
        "count": len(tracks),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": "spotify_api",
    }

def spotify_embed_fetch_collection(url: str, force_refresh: bool = False, write_cache: bool = True) -> Optional[Dict[str, Any]]:
    norm_url = normalize_spotify_url(url)
    entity_type = spotify_detect_entity_type(norm_url)
    entity_id = spotify_extract_entity_id(norm_url, entity_type)
    if not entity_id or entity_type not in SPOTIFY_ENTITY_TYPES:
        log_error(f"[SPOTIFY_EMBED] Invalid Spotify URL: {url}")
        return None

    if force_refresh:
        api_result = spotify_api_fetch_collection(norm_url)
        if api_result and api_result.get("tracks"):
            if write_cache:
                cache = load_embed_cache()
                cache[norm_url] = api_result
                save_embed_cache(cache)
            log(f"✅ Spotify API reescan OK: {api_result.get('name') or norm_url} | tracks={api_result.get('count', 0)}")
            return api_result

    cache = load_embed_cache()
    cached = cache.get(norm_url)
    if not force_refresh and cached and isinstance(cached, dict) and cached.get("tracks"):
        log(f"🗂️ Usando cache do embed Spotify: {norm_url}")
        return cached
    if force_refresh and cached:
        log(f"🔄 Reescan ativo: ignorando cache do embed Spotify: {norm_url}")

    if SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET:
        api_result = spotify_api_fetch_collection(norm_url)
        if api_result and api_result.get("tracks"):
            if write_cache:
                cache[norm_url] = api_result
                save_embed_cache(cache)
            log(f"✅ Spotify API OK: {api_result.get('name') or norm_url} | tracks={api_result.get('count', 0)}")
            return api_result

    embed_url = f"https://open.spotify.com/embed/{entity_type}/{entity_id}"
    log(f"🌐 Lendo {entity_type} do embed Spotify: {embed_url}")
    html_text = spotify_embed_http_get_text(embed_url, timeout=SPOTIFY_EMBED_TIMEOUT_SECONDS)
    if not html_text:
        return None

    if write_cache:
        try:
            with open(SPOTIFY_EMBED_DEBUG_FILE, "w", encoding="utf-8") as f:
                f.write(html_text)
        except Exception as e:
            log_error(f"[SPOTIFY_EMBED] Failed to save debug html: {e}")

    parsed = None
    next_data = spotify_extract_next_data(html_text)
    if next_data:
        parsed = spotify_parse_embed_tracklist(next_data)
        if not parsed or not parsed.get("tracks"):
            parsed = spotify_parse_tracklist_deep(next_data)

    if not parsed or not parsed.get("tracks"):
        parsed = spotify_parse_embed_tracklist_from_html(html_text)

    if not parsed.get("tracks"):
        log_error(f"[SPOTIFY_EMBED] trackList empty: {embed_url}")
        if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
            log_error("[SPOTIFY_API] Configure spotify.client_id e spotify.client_secret para usar a API oficial quando o embed publico falhar.")
        return None

    result = {
        "url": norm_url,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "name": parsed.get("name", ""),
        "uri": parsed.get("uri", ""),
        "tracks": parsed.get("tracks", []),
        "count": parsed.get("count", 0),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": "spotify_embed",
    }
    if write_cache:
        cache[norm_url] = result
        save_embed_cache(cache)
    return result

def run_spotify_playlist(
    url: str,
    genero: str,
    hist: Set[str],
    baixados: List[str],
    downloaded_items: List[Dict[str, Any]],
    reescan_list: bool = False,
    dry_run: bool = False,
) -> Dict[str, int]:
    stats = {
        "collections": 1,
        "playlists": 0,
        "artists": 0,
        "new": 0,
        "existing": 0,
        "history": 0,
        "dry_run": 0,
        "failed": 0,
    }
    norm_url = normalize_spotify_url(url)
    pid = spotify_entity_history_id(norm_url)
    entity_type_for_stats = spotify_detect_entity_type(norm_url)
    if entity_type_for_stats == "artist":
        stats["artists"] = 1
    else:
        stats["playlists"] = 1

    if SPOTIFY_MODE in ("OFF", "YOUTUBE_ONLY"):
        log(f"Spotify ignorado (SPOTIFY_MODE={SPOTIFY_MODE}). Pulando: {norm_url}")
        return stats

    if SPOTIFY_MODE == "INDEX_ONLY":
        if not dry_run:
            hist.add(pid)
        log(f"INDEX_ONLY: marcado no historico (sem requests): {norm_url}")
        return stats

    if pid in hist and not reescan_list:
        log(f"Spotify playlist ja processada: {norm_url}")
        stats["history"] += 1
        return stats

    collection = spotify_embed_fetch_collection(norm_url, force_refresh=reescan_list, write_cache=not dry_run)
    if not collection or not collection.get("tracks"):
        log(f"Nao foi possivel extrair musicas do Spotify: {norm_url}")
        stats["failed"] += 1
        return stats

    target_folder = None
    existing_keys: Set[str] = set()
    use_history = True

    if reescan_list:
        target_folder = os.path.join(MUSIC_DIR, safe_name(genero) if genero else "Sem_Genero")
        if not os.path.exists(target_folder):
            if dry_run:
                log(f"DRY-RUN criaria pasta do genero: {target_folder}")
            else:
                os.makedirs(target_folder, exist_ok=True)
                log(f"Pasta do genero nao existe. Criada: {target_folder}")
        else:
            existing_keys = list_existing_track_keys(target_folder)
            log(f"Reescan ativo em {target_folder} | chaves locais encontradas={len(existing_keys)}")

    count_ok = 0
    count_skip_existing = 0
    count_skip_history = 0
    count_failed = 0
    count_dry_run = 0

    for item in collection.get("tracks") or []:
        artist = (item.get("artist") or "").strip()
        title = (item.get("title") or "").strip()
        if not artist or not title:
            continue

        if reescan_list and existing_keys.intersection(track_match_keys(artist, title)):
            count_skip_existing += 1
            debug(f"Skip by folder scan: {artist} - {title}")
            continue

        status, out = run_youtube_track(
            artist,
            title,
            genero,
            hist,
            target_folder=target_folder,
            use_history=use_history,
            dry_run=dry_run,
        )
        if status == "downloaded" and out:
            baixados.append(out)
            downloaded_items.append({
                "path": out,
                "meta": {
                    "artist": artist,
                    "title": title,
                    "album": (item.get("album") or collection.get("name") or "").strip(),
                    "genre": genero,
                },
            })
            count_ok += 1
        elif status == "skipped_existing":
            count_skip_existing += 1
        elif status == "skipped_history":
            count_skip_history += 1
        elif status == "dry_run":
            count_dry_run += 1
        elif status == "failed":
            count_failed += 1

    can_mark_done_with_failures = MARK_COLLECTION_DONE_WITH_FAILURES and count_failed <= MAX_FAILURES_TO_MARK_DONE
    if not dry_run and (count_failed == 0 or can_mark_done_with_failures):
        hist.add(pid)
    elif count_failed:
        log(f"Playlist nao marcada como concluida porque houve falhas: {norm_url} | falhas={count_failed}")

    entity_label = "artista" if (collection.get("entity_type") == "artist") else "playlist"
    extra = f" | ja_existentes={count_skip_existing}" if reescan_list else ""
    log(f"{entity_label.capitalize()} processado: {collection.get('name') or norm_url} | novas={count_ok}{extra} | historico={count_skip_history} | dry_run={count_dry_run} | falhas={count_failed} | total_indexadas={collection.get('count', 0)}")
    stats["new"] += count_ok
    stats["existing"] += count_skip_existing
    stats["history"] += count_skip_history
    stats["dry_run"] += count_dry_run
    stats["failed"] += count_failed
    return stats


def track_match_keys(artist: str, title: str) -> Set[str]:
    artist_key = normalize_loose(artist)
    title_key = normalize_loose(title)
    keys = set()
    if artist_key and title_key:
        keys.add(f"{artist_key}|{title_key}")
        first_artist = normalize_loose(re.split(r",|&| feat\.? | ft\.? ", artist, maxsplit=1, flags=re.I)[0])
        if first_artist and first_artist != artist_key:
            keys.add(f"{first_artist}|{title_key}")
    if title_key:
        keys.add(f"TITLE:{title_key}")
    return keys
def list_existing_track_keys(folder: str) -> Set[str]:
    keys: Set[str] = set()
    if not folder or not os.path.exists(folder):
        return keys

    for fpath in iter_audio_files(folder):
        meta = parse_from_filename(fpath)
        keys.update(track_match_keys(meta.get("artist", ""), meta.get("title", "")))
    return keys

# =========================
# Tagging mode
# =========================
def iter_audio_files(root: str) -> List[str]:
    p = Path(root)
    if not p.exists():
        return []
    files: List[str] = []
    for fp in p.rglob("*"):
        if fp.is_file() and fp.suffix.lower() in AUDIO_EXTS:
            files.append(str(fp))
    return files

def parse_from_filename(path: str) -> Dict[str, str]:
    fp = Path(path)
    rel = None
    parts = []
    try:
        rel = fp.relative_to(Path(MUSIC_DIR))
        parts = list(rel.parts)
    except Exception:
        parts = list(fp.parts)

    genre = ""
    album = ""
    if rel is not None:
        if len(parts) >= 2:
            genre = parts[0]
        if len(parts) >= 3:
            album = parts[1]

    name = fp.stem
    name_clean = re.sub(r"\s*\(\s*\d+\s*bpm\s*\)\s*$", "", name, flags=re.I).strip()
    name_clean = re.sub(r"\s*\(\s*duplicate\s*\)\s*$", "", name_clean, flags=re.I).strip()

    artist = ""
    title = name_clean
    m = re.match(r"^(?P<artist>.+?)\s*-\s*(?P<title>.+)$", name_clean)
    if m:
        artist = m.group("artist").strip()
        title = m.group("title").strip()

    return {"artist": artist, "title": title, "album": album, "genre": genre}

def tag_mp3(path: str, meta: Dict[str, str], only_fill_missing: bool = True) -> bool:
    if EasyID3 is None:
        raise RuntimeError("mutagen não está instalado. Instale com: pip install mutagen")
    changed = False
    try:
        audio = EasyID3(path)
    except Exception:
        audio = EasyID3()
        audio.save(path)
        audio = EasyID3(path)

    def set_field(key: str, value: str):
        nonlocal changed
        if not value:
            return
        cur = audio.get(key, [])
        if only_fill_missing and cur:
            return
        audio[key] = [value]
        changed = True

    set_field("artist", meta.get("artist", ""))
    set_field("title", meta.get("title", ""))
    set_field("album", meta.get("album", ""))
    set_field("genre", meta.get("genre", ""))

    if changed:
        audio.save()
    return changed

def tag_m4a(path: str, meta: Dict[str, str], only_fill_missing: bool = True) -> bool:
    if MP4 is None:
        raise RuntimeError("mutagen não está instalado. Instale com: pip install mutagen")
    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()
    changed = False

    def set_mp4(key: str, value: str):
        nonlocal changed
        if not value:
            return
        cur = audio.tags.get(key) if audio.tags else None
        if only_fill_missing and cur:
            return
        audio.tags[key] = [value]
        changed = True

    set_mp4("\xa9ART", meta.get("artist", ""))
    set_mp4("\xa9nam", meta.get("title", ""))
    set_mp4("\xa9alb", meta.get("album", ""))
    set_mp4("\xa9gen", meta.get("genre", ""))

    if changed:
        audio.save()
    return changed

def tag_music_item(path: str, meta: Optional[Dict[str, str]] = None, only_fill_missing: bool = True) -> bool:
    full_meta = parse_from_filename(path)
    for key, value in (meta or {}).items():
        if value:
            full_meta[key] = str(value).strip()
    ext = Path(path).suffix.lower()
    if ext == ".mp3":
        return tag_mp3(path, full_meta, only_fill_missing=only_fill_missing)
    if ext in (".m4a", ".mp4"):
        return tag_m4a(path, full_meta, only_fill_missing=only_fill_missing)
    return False

def tag_music_files(files: List[str], only_fill_missing: bool = True, label: str = "Tagging") -> None:
    if not files:
        log("⚠️ Nenhum arquivo de áudio para taguear.")
        return

    log(f"🏷️ {label}: {len(files)} arquivos")
    tagged = 0
    skipped = 0
    failed = 0

    for fpath in tqdm(files, desc="Tagging", unit="file", dynamic_ncols=True):
        try:
            changed = tag_music_item(fpath, only_fill_missing=only_fill_missing)

            if changed:
                tagged += 1
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            log_error(f"[TAG] {fpath} :: {e}")

    log(f"✅ Tagging concluído. alterados={tagged} | pulados={skipped} | erros={failed}")

def tag_downloaded_items(items: List[Dict[str, Any]], only_fill_missing: bool = True) -> None:
    if not items:
        log("⚠️ Nenhum arquivo novo para auto-tag.")
        return

    tagged = 0
    skipped = 0
    failed = 0
    log(f"🏷️ Auto-tag arquivos novos: {len(items)} arquivos")

    for item in tqdm(items, desc="Auto-tag", unit="file", dynamic_ncols=True):
        path = str(item.get("path") or "")
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        if not path:
            skipped += 1
            continue
        try:
            if tag_music_item(path, meta=meta, only_fill_missing=only_fill_missing):
                tagged += 1
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            log_error(f"[AUTO_TAG] {path} :: {e}")

    log(f"✅ Auto-tag concluído. alterados={tagged} | pulados={skipped} | erros={failed}")

def tag_music_library(root: str, only_fill_missing: bool = True) -> None:
    files = iter_audio_files(root)
    if not files:
        log(f"⚠️ Nenhum arquivo de áudio encontrado em: {root}")
        return
    tag_music_files(files, only_fill_missing=only_fill_missing, label=f"Tagging mode em {root}")

def new_run_stats() -> Dict[str, int]:
    return {
        "rows": 0,
        "manual_tracks": 0,
        "collections": 0,
        "playlists": 0,
        "artists": 0,
        "new": 0,
        "existing": 0,
        "history": 0,
        "dry_run": 0,
        "failed": 0,
        "ignored_rows": 0,
    }

def merge_stats(target: Dict[str, int], source: Dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value or 0)

def status_to_stats(status: str) -> Dict[str, int]:
    if status == "downloaded":
        return {"new": 1}
    if status == "skipped_existing":
        return {"existing": 1}
    if status == "skipped_history":
        return {"history": 1}
    if status == "dry_run":
        return {"dry_run": 1}
    if status == "failed":
        return {"failed": 1}
    return {}

# =========================
# Conversion mode
# =========================
def iter_files_by_extension(root: str, extension: str) -> List[str]:
    base = Path(root)
    if not base.exists():
        return []
    suffix = "." + extension.lower().lstrip(".")
    return [str(fp) for fp in base.rglob("*") if fp.is_file() and fp.suffix.lower() == suffix]

def conversion_destination_path(source_path: str, destination_format: str) -> str:
    fp = Path(source_path)
    return str(fp.with_suffix("." + destination_format.lower().lstrip(".")))

def ffmpeg_conversion_command(source_path: str, destination_path: str, destination_format: str) -> List[str]:
    cmd = ["ffmpeg", "-y", "-i", source_path]
    if destination_format == "mp3":
        cmd += ["-vn", "-codec:a", "libmp3lame", "-b:a", f"{QUALITY_AUDIO}k"]
    else:
        cmd += ["-vn"]
    cmd += ["-threads", str(CONVERSION_FFMPEG_THREADS)]
    cmd.append(destination_path)
    return cmd

def convert_audio_file(source_path: str, destination_format: str, dry_run: bool, delete_source: bool, verbose: bool) -> str:
    destination_path = conversion_destination_path(source_path, destination_format)
    if os.path.exists(destination_path):
        if verbose:
            log(f"Conversao ignorada, destino ja existe: {destination_path}")
        return "skipped_existing"

    cmd = ffmpeg_conversion_command(source_path, destination_path, destination_format)
    if dry_run:
        log(f"DRY-RUN converteria: {source_path} -> {destination_path}")
        if delete_source:
            log(f"DRY-RUN apagaria origem apos sucesso: {source_path}")
        return "dry_run"

    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    if result.returncode != 0:
        if not verbose:
            log_error(f"[CONVERSION] ffmpeg failed {source_path}: {result.stderr}")
        return "failed"

    if delete_source:
        try:
            os.remove(source_path)
        except Exception as e:
            log_error(f"[CONVERSION] converted but failed to delete source {source_path}: {e}")
            return "converted_delete_failed"

    if verbose:
        log(f"Convertido: {source_path} -> {destination_path}")
    return "converted"

def run_conversion_mode() -> Dict[str, int]:
    if not CONVERSION_ENABLE:
        log("Conversao desativada no config.")
        return {"found": 0, "converted": 0, "skipped_existing": 0, "dry_run": 0, "failed": 0}
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Conversao precisa do ffmpeg instalado e disponivel no PATH.")

    files = iter_files_by_extension(CONVERSION_MUSIC_DIR, CONVERSION_SOURCE_FORMAT)
    stats = {"found": len(files), "converted": 0, "skipped_existing": 0, "dry_run": 0, "failed": 0}
    log(
        "Conversao: "
        f"{CONVERSION_SOURCE_FORMAT} -> {CONVERSION_DESTINATION_FORMAT} | "
        f"arquivos={len(files)} | dry_run={'SIM' if CONVERSION_DRY_RUN else 'NAO'} | "
        f"delete_source={'SIM' if CONVERSION_DELETE_SOURCE else 'NAO'} | "
        f"workers={CONVERSION_WORKERS} | ffmpeg_threads={CONVERSION_FFMPEG_THREADS}"
    )

    def collect_status(status: str) -> None:
        if status == "converted_delete_failed":
            stats["converted"] += 1
            stats["failed"] += 1
        elif status in stats:
            stats[status] += 1

    def convert_one(source_path: str) -> str:
        return convert_audio_file(
            source_path,
            CONVERSION_DESTINATION_FORMAT,
            dry_run=CONVERSION_DRY_RUN,
            delete_source=CONVERSION_DELETE_SOURCE,
            verbose=CONVERSION_VERBOSE,
        )

    if CONVERSION_WORKERS == 1 or len(files) <= 1:
        for source_path in tqdm(files, desc="Converting", unit="file", dynamic_ncols=True):
            collect_status(convert_one(source_path))
    else:
        with ThreadPoolExecutor(max_workers=CONVERSION_WORKERS) as executor:
            futures = [executor.submit(convert_one, source_path) for source_path in files]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Converting", unit="file", dynamic_ncols=True):
                try:
                    collect_status(future.result())
                except Exception as e:
                    stats["failed"] += 1
                    log_error(f"[CONVERSION] falha inesperada: {e}")

    log(
        "Conversao concluida: "
        f"encontrados={stats['found']} | convertidos={stats['converted']} | "
        f"existentes={stats['skipped_existing']} | dry_run={stats['dry_run']} | falhas={stats['failed']}"
    )
    return stats

# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(description="Spotify embed playlist index + yt-dlp downloader")
    parser.add_argument("--tagmusic", dest="tagmusic", action=argparse.BooleanOptionalAction, default=None, help="Ignora downloads e aplica tags basicas em MUSIC_DIR")
    parser.add_argument("--tag-force", dest="tag_force", action=argparse.BooleanOptionalAction, default=None, help="Sobrescreve tags existentes no modo --tagmusic")
    parser.add_argument("--reescan-list", dest="reescan_list", action=argparse.BooleanOptionalAction, default=None, help="Para playlists/artistas do Spotify, verifica a pasta e baixa so faixas novas")
    parser.add_argument("--dry-run", dest="dry_run", action=argparse.BooleanOptionalAction, default=None, help="Mostra o que faria, mas nao baixa musicas nem grava historico")
    parser.add_argument("--only-row", type=int, default=None, help="Processa apenas uma linha da planilha (1-based)")
    parser.add_argument("--only-url", default=None, help="Processa apenas uma URL Spotify informada")
    parser.add_argument("--input-file", default=None, help="CSV local para processar no lugar da planilha do config")
    parser.add_argument("--conversion-only", dest="conversion_only", action=argparse.BooleanOptionalAction, default=None, help="Executa apenas a conversao de arquivos de audio")
    args, _ = parser.parse_known_args()
    reescan_list = config_bool("execution.reescan_list", False) if args.reescan_list is None else args.reescan_list
    dry_run = config_bool("execution.dry_run", False) if args.dry_run is None else args.dry_run
    tagmusic = config_bool("execution.tagmusic", False) if args.tagmusic is None else args.tagmusic
    tag_force = config_bool("execution.tag_force", False) if args.tag_force is None else args.tag_force
    only_row = args.only_row if args.only_row is not None else config_value("execution.only_row")
    only_url = args.only_url if args.only_url is not None else config_str("execution.only_url", "")
    input_file = args.input_file
    conversion_only = CONVERSION_ONLY if args.conversion_only is None else args.conversion_only

    if tagmusic:
        tag_music_library(MUSIC_DIR, only_fill_missing=not tag_force)
        return

    if conversion_only:
        run_conversion_mode()
        return

    if not input_file and not GOOGLE_SHEET_CSV:
        raise RuntimeError("google_sheet_csv nao foi definido no config.yaml")

    if AUDIO_FORMAT == "mp3" and not shutil.which("ffmpeg"):
        raise RuntimeError("AUDIO_FORMAT=mp3 precisa do ffmpeg instalado e disponivel no PATH.")

    log("Starting...")
    log(f"Modo reescan playlists/artistas: {'SIM' if reescan_list else 'NAO'}")
    log(f"Modo teste sem baixar: {'SIM' if dry_run else 'NAO'}")
    log(f"Entrada: {input_file or GOOGLE_SHEET_CSV}")
    log(f"Pastas: music={MUSIC_DIR} | state={STATE_DIR}")
    if YTDLP_COOKIES_FROM_BROWSER:
        log(f"yt-dlp cookies do navegador: {YTDLP_COOKIES_FROM_BROWSER}")
    hist = load_history()
    baixados: List[str] = []
    downloaded_items: List[Dict[str, Any]] = []
    run_stats = new_run_stats()

    df = pd.read_csv(input_file or GOOGLE_SHEET_CSV)
    if only_url:
        df = pd.DataFrame([{"Artista": only_url, "Musica": "", "(opcional) Tag/Genero": ""}])
    elif only_row:
        row_number = int(only_row)
        if row_number < 1 or row_number > len(df):
            raise RuntimeError(f"only_row fora do intervalo: {row_number} (planilha tem {len(df)} linhas)")
        df = df.iloc[[row_number - 1]]

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing", unit="it", dynamic_ncols=True):
        run_stats["rows"] += 1
        try:
            spotify_url = ""
            for value in row.tolist():
                value = "" if is_nan(value) else str(value).strip()
                if value and is_spotify_url(value):
                    spotify_url = value
                    break

            genero = row.get("(opcional) Tag/Genero", "")
            genero = "" if is_nan(genero) else str(genero).strip()

            if spotify_url:
                merge_stats(
                    run_stats,
                    run_spotify_playlist(spotify_url, genero, hist, baixados, downloaded_items, reescan_list=reescan_list, dry_run=dry_run),
                )
                continue

            artist = row.get("Artista", "")
            title = row.get("Musica", "")
            artist = "" if is_nan(artist) else str(artist).strip()
            title = "" if is_nan(title) else str(title).strip()

            if not artist or not title:
                run_stats["ignored_rows"] += 1
                log_error(f"[SHEET] Row {idx+1} ignored: missing Artista/Musica and not Spotify URL.")
                continue

            run_stats["manual_tracks"] += 1
            status, out = run_youtube_track(artist, title, genero, hist, dry_run=dry_run)
            merge_stats(run_stats, status_to_stats(status))
            if status == "failed":
                log_failed_item("manual", "download failed", artist=artist, title=title, genre=genero, row_number=int(idx) + 1)
            if status == "downloaded" and out:
                baixados.append(out)
                downloaded_items.append({
                    "path": out,
                    "meta": {
                        "artist": artist,
                        "title": title,
                        "album": "",
                        "genre": genero,
                    },
                })

        except Exception as e:
            run_stats["failed"] += 1
            log_error(f"[MAIN] Row {idx+1} exception: {e}")
            log_failed_item("row", str(e), row_number=int(idx) + 1)
            continue

    if dry_run:
        log("DRY-RUN: nenhum arquivo de estado foi salvo.")
    else:
        save_baixados(baixados)
        save_history(hist)
        if AUTO_TAG_AFTER_DOWNLOAD:
            if downloaded_items:
                log("Auto-tag ativo: preenchendo metadados dos arquivos novos...")
                tag_downloaded_items(downloaded_items, only_fill_missing=not AUTO_TAG_FORCE)
            else:
                log("Auto-tag ativo, mas nenhum download novo foi registrado.")
    log(
        "Resumo: "
        f"linhas={run_stats['rows']} | playlists={run_stats['playlists']} | artistas={run_stats['artists']} | "
        f"manuais={run_stats['manual_tracks']} | novas={run_stats['new']} | existentes={run_stats['existing']} | "
        f"historico={run_stats['history']} | dry_run={run_stats['dry_run']} | falhas={run_stats['failed']} | ignoradas={run_stats['ignored_rows']}"
    )
    log(f"Done. baixados={len(baixados)} | state={STATE_DIR} | music={MUSIC_DIR}")

if __name__ == "__main__":
    main()
