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
import hashlib
import unicodedata
from difflib import SequenceMatcher
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
import certifi
from tqdm import tqdm

from google_sheets import normalize_google_sheet_csv_url
from row_selection import parse_row_selection

try:
    import numpy as np
except Exception:
    np = None

try:
    import librosa
except Exception:
    librosa = None

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


def _finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None

# =========================
# Config
# =========================
MUSIC_DIR = config_str("paths.music_dir", "/data/music")
STATE_DIR = config_str("paths.state_dir", "/data/state")

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
YTDLP_SEARCH_QUERY_LIMIT = config_int("ytdlp.search_query_limit", 3)
YTDLP_CANDIDATE_LIMIT = config_int("ytdlp.candidate_limit", 6)
YTDLP_DOWNLOAD_ATTEMPTS = config_int("ytdlp.download_attempts", 3)
YTDLP_PREFER_OFFICIAL = config_bool("ytdlp.prefer_official", True)
YTDLP_MIN_SOURCE_BITRATE_KBPS = config_int("ytdlp.min_source_bitrate_kbps", 120)
YTDLP_SPECTRAL_CHECK = config_bool("ytdlp.spectral_check", True)
YTDLP_SPECTRAL_CUTOFF_HZ = config_int("ytdlp.spectral_cutoff_hz", 17000)
YTDLP_SPECTRAL_DROP_DB = config_int("ytdlp.spectral_drop_db", 20)
YTDLP_SPECTRAL_SECONDS = config_int("ytdlp.spectral_seconds", 60)
YTDLP_EXTRACTOR_RETRIES = config_int("ytdlp.extractor_retries", 3)

SPOTIFY_MODE = config_str("spotify.mode", "EMBED").upper()
SPOTIFY_EMBED_TIMEOUT_SECONDS = config_int("spotify.embed_timeout_seconds", 20)

GOOGLE_SHEET_CSV = normalize_google_sheet_csv_url(config_str("source.google_sheet_csv", ""))
LOG_LEVEL = config_str("execution.log_level", "INFO").upper()
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

AUDIO_EXTS = {".mp3", ".m4a", ".mp4", ".flac", ".wav", ".aiff", ".aif"}
YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN = False


def ensure_runtime_dirs() -> None:
    os.makedirs(MUSIC_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)

if DISABLE_SSL_VERIFY:
    ssl._create_default_https_context = ssl._create_unverified_context

def validate_config() -> None:
    errors = []
    if AUDIO_FORMAT not in ("mp3", "m4a"):
        errors.append("audio.format deve ser 'mp3' ou 'm4a'.")
    if SPOTIFY_MODE not in ("EMBED", "INDEX_ONLY", "YOUTUBE_ONLY", "OFF"):
        errors.append("spotify.mode deve ser EMBED, INDEX_ONLY, YOUTUBE_ONLY ou OFF.")
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
    if YTDLP_SEARCH_QUERY_LIMIT < 1:
        errors.append("ytdlp.search_query_limit precisa ser maior ou igual a 1.")
    if YTDLP_CANDIDATE_LIMIT < 1:
        errors.append("ytdlp.candidate_limit precisa ser maior ou igual a 1.")
    if YTDLP_DOWNLOAD_ATTEMPTS < 1:
        errors.append("ytdlp.download_attempts precisa ser maior ou igual a 1.")
    if YTDLP_MIN_SOURCE_BITRATE_KBPS < 1:
        errors.append("ytdlp.min_source_bitrate_kbps precisa ser maior ou igual a 1.")
    if YTDLP_SPECTRAL_CUTOFF_HZ < 8000:
        errors.append("ytdlp.spectral_cutoff_hz precisa ser maior ou igual a 8000.")
    if YTDLP_SPECTRAL_DROP_DB < 1:
        errors.append("ytdlp.spectral_drop_db precisa ser maior ou igual a 1.")
    if YTDLP_SPECTRAL_SECONDS < 5:
        errors.append("ytdlp.spectral_seconds precisa ser maior ou igual a 5.")
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
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if s.split(".", 1)[0].upper() in reserved:
        s = "_" + s
    if len(s) > 160:
        digest = hashlib.sha1(s.encode("utf-8", errors="replace")).hexdigest()[:10]
        s = s[:145].rstrip(". ") + "-" + digest
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
def bundled_ffmpeg_dir() -> Optional[str]:
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    roots = [
        Path.cwd(),
        Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None,
        Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None,
    ]
    for root in roots:
        if not root:
            continue
        for candidate in (root / "vendor" / "ffmpeg", root / "_internal" / "vendor" / "ffmpeg"):
            if (candidate / ffmpeg_name).exists() and (candidate / ffprobe_name).exists():
                return str(candidate)
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe and Path(ffmpeg).parent == Path(ffprobe).parent:
        return str(Path(ffmpeg).parent)
    return None


def _youtube_format_description(audio_format: Dict[str, Any]) -> str:
    if not audio_format:
        return "fonte de audio nao informada"
    parts = []
    format_id = str(audio_format.get("format_id") or "").strip()
    codec = str(audio_format.get("acodec") or "").strip()
    extension = str(audio_format.get("ext") or "").strip()
    abr = _finite_float(audio_format.get("abr"))
    tbr = _finite_float(audio_format.get("tbr"))
    bitrate = abr if abr is not None else (tbr if str(audio_format.get("vcodec") or "none") == "none" else None)
    sample_rate = _finite_float(audio_format.get("asr"))
    if format_id:
        parts.append(f"formato {format_id}")
    if codec and codec != "none":
        parts.append(codec)
    elif extension:
        parts.append(extension)
    if bitrate is not None:
        parts.append(f"~{bitrate:.0f} kbps")
    if sample_rate is not None:
        parts.append(f"{sample_rate / 1000:g} kHz")
    return " | ".join(parts) or "fonte de audio nao informada"


def youtube_source_progress_hook(event: Dict[str, Any]) -> None:
    if str(event.get("status") or "") != "finished":
        return
    info = event.get("info_dict") if isinstance(event.get("info_dict"), dict) else {}
    description = _youtube_format_description(info)
    log(f"Fonte baixada do YouTube: {description}")
    if AUDIO_FORMAT != "mp3":
        return
    source_bitrate = _finite_float(info.get("abr"))
    if source_bitrate is None and str(info.get("vcodec") or "none") == "none":
        source_bitrate = _finite_float(info.get("tbr"))
    target_bitrate = _finite_float(QUALITY_AUDIO)
    if source_bitrate is not None and target_bitrate is not None and target_bitrate > source_bitrate:
        log(
            f"Conversao: fonte ~{source_bitrate:.0f} kbps -> MP3 {target_bitrate:.0f} kbps. "
            "A conversao preserva compatibilidade, mas nao cria qualidade ausente na fonte."
        )


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
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": YTDLP_EXTRACTOR_RETRIES,
        "concurrent_fragment_downloads": YTDLP_CONCURRENT_FRAGMENTS,
        "extractor_args": {"youtube": {"player_client": YTDLP_PLAYER_CLIENTS or [YTDLP_PLAYER_CLIENT]}},
        "postprocessors": postprocessors,
        "progress_hooks": [youtube_source_progress_hook],
        "embed_metadata": EMBED_METADATA,
        "add_metadata": EMBED_METADATA,
        "embed_thumbnail": EMBED_THUMBNAIL,
    }

    if use_browser_cookies and not YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN and YTDLP_COOKIES_FROM_BROWSER and YTDLP_COOKIES_FROM_BROWSER.lower() not in ("0", "none", "off", "false", "no"):
        opts["cookiesfrombrowser"] = (YTDLP_COOKIES_FROM_BROWSER,)

    if YTDLP_REMOTE_COMPONENTS:
        opts["remote_components"] = YTDLP_REMOTE_COMPONENTS

    ffmpeg_dir = bundled_ffmpeg_dir()
    if ffmpeg_dir:
        opts["ffmpeg_location"] = ffmpeg_dir

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
    ffmpeg_dir = bundled_ffmpeg_dir()
    ffmpeg_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    ffmpeg_exe = str(Path(ffmpeg_dir) / ffmpeg_name) if ffmpeg_dir else (shutil.which("ffmpeg") or "")
    if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):
        log_error(f"[YOUTUBE] Nao foi possivel converter para mp3 sem ffmpeg: {source_path}")
        return None
    cmd = [ffmpeg_exe, "-y", "-i", str(source), "-vn", "-codec:a", "libmp3lame", "-b:a", f"{QUALITY_AUDIO}k", destination]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        log_error(f"[YOUTUBE] ffmpeg falhou ao converter {source_path}: {result.stderr}")
        return None
    log(f"Convertido para mp3: {os.path.basename(destination)}")
    return destination

def build_search_queries(artist: str, title: str) -> List[str]:
    terms = YTDLP_SEARCH_TERMS or [""]
    title_key = normalize_loose(title)
    default_priority = {
        "official audio": 0,
        "official music video": 1,
        "audio": 2,
        "extended": 3,
        "lyrics": 4,
    }
    terms = sorted(
        enumerate(terms),
        key=lambda pair: (
            -1 if normalize_loose(pair[1]) and normalize_loose(pair[1]) in title_key else default_priority.get(normalize_loose(pair[1]), 10),
            pair[0],
        ),
    )
    queries = []
    seen = set()
    for _, term in terms[:max(1, YTDLP_SEARCH_QUERY_LIMIT)]:
        query = YTDLP_QUERY_TEMPLATE.format(artist=artist, title=title, term=term).strip()
        query = re.sub(r"\s+", " ", query)
        key = normalize_loose(query)
        if query and key not in seen:
            queries.append(query)
            seen.add(key)
    return queries


def _youtube_entry_url(entry: Dict[str, Any]) -> str:
    return str(entry.get("webpage_url") or entry.get("original_url") or entry.get("url") or "").strip()


def _youtube_audio_formats(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    formats = [item for item in (entry.get("formats") or []) if isinstance(item, dict)]
    audio_only = [
        item for item in formats
        if str(item.get("acodec") or "none") != "none" and str(item.get("vcodec") or "none") == "none"
    ]
    if audio_only:
        return audio_only
    return [item for item in formats if str(item.get("acodec") or "none") != "none"]


def best_youtube_audio_format(entry: Dict[str, Any]) -> Dict[str, Any]:
    formats = _youtube_audio_formats(entry)
    if not formats:
        return {}

    def quality_key(item: Dict[str, Any]) -> Tuple[float, float, float, int]:
        abr = _finite_float(item.get("abr"))
        tbr = _finite_float(item.get("tbr"))
        sample_rate = _finite_float(item.get("asr"))
        bitrate = abr if abr is not None else (tbr if str(item.get("vcodec") or "none") == "none" else 0.0)
        return (
            _finite_float(item.get("quality")) or 0.0,
            bitrate or 0.0,
            sample_rate or 0.0,
            formats.index(item),
        )

    return max(formats, key=quality_key)


def youtube_audio_bitrate_kbps(entry: Dict[str, Any]) -> Optional[float]:
    audio_format = best_youtube_audio_format(entry)
    abr = _finite_float(audio_format.get("abr"))
    if abr is not None:
        return abr
    if str(audio_format.get("vcodec") or "none") == "none":
        return _finite_float(audio_format.get("tbr"))
    return None


def youtube_source_quality_tier(entry: Dict[str, Any]) -> int:
    bitrate = youtube_audio_bitrate_kbps(entry)
    if bitrate is None:
        return 1
    return 2 if bitrate >= max(1, YTDLP_MIN_SOURCE_BITRATE_KBPS) else 0


def youtube_source_description(entry: Dict[str, Any]) -> str:
    audio_format = best_youtube_audio_format(entry)
    return _youtube_format_description(audio_format)


def evaluate_spectral_profile(frequencies: Any, peak_magnitude: Any) -> Dict[str, Any]:
    if np is None:
        return {"available": False, "suspicious": False, "reason": "numpy indisponivel"}
    frequency_values = np.asarray(frequencies, dtype=float)
    magnitude_values = np.asarray(peak_magnitude, dtype=float)
    valid = np.isfinite(frequency_values) & np.isfinite(magnitude_values) & (magnitude_values >= 0)
    frequency_values = frequency_values[valid]
    magnitude_values = magnitude_values[valid]
    if frequency_values.size < 8 or magnitude_values.size < 8:
        return {"available": False, "suspicious": False, "reason": "amostra espectral insuficiente"}
    reference = float(np.max(magnitude_values))
    if not math.isfinite(reference) or reference <= 1e-12:
        return {"available": False, "suspicious": False, "reason": "audio silencioso"}

    def band_level_db(start_hz: float, end_hz: float) -> Optional[float]:
        mask = (frequency_values >= start_hz) & (frequency_values < end_hz)
        if not np.any(mask):
            return None
        rms = float(np.sqrt(np.mean(np.square(magnitude_values[mask]))))
        return 20.0 * math.log10(max(rms, reference * 1e-12) / reference)

    band_width = 200
    band_centers = []
    band_levels = []
    nyquist = float(np.max(frequency_values))
    start_hz = 0
    while start_hz < nyquist:
        level = band_level_db(start_hz, min(nyquist + 1, start_hz + band_width))
        if level is not None:
            band_centers.append(start_hz + band_width / 2)
            band_levels.append(level)
        start_hz += band_width
    active_bands = [center for center, level in zip(band_centers, band_levels) if level >= -60.0]
    cutoff_hz = max(active_bands) if active_bands else 0.0
    lower_level = band_level_db(14000, 16000)
    upper_level = band_level_db(17500, min(20500, nyquist + 1))
    drop_db = None
    if lower_level is not None and upper_level is not None:
        drop_db = upper_level - lower_level
    suspicious = bool(
        cutoff_hz < YTDLP_SPECTRAL_CUTOFF_HZ
        and lower_level is not None
        and lower_level > -55.0
        and drop_db is not None
        and drop_db <= -abs(YTDLP_SPECTRAL_DROP_DB)
    )
    return {
        "available": True,
        "suspicious": suspicious,
        "cutoff_hz": round(cutoff_hz),
        "lower_band_db": round(lower_level, 1) if lower_level is not None else None,
        "upper_band_db": round(upper_level, 1) if upper_level is not None else None,
        "drop_db": round(drop_db, 1) if drop_db is not None else None,
    }


def inspect_downloaded_spectrum(path: str) -> Dict[str, Any]:
    if not YTDLP_SPECTRAL_CHECK:
        return {"available": False, "suspicious": False, "reason": "verificacao desativada"}
    if np is None:
        return {"available": False, "suspicious": False, "reason": "numpy indisponivel"}
    try:
        ffmpeg_dir = bundled_ffmpeg_dir()
        executable_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        ffmpeg = str(Path(ffmpeg_dir) / executable_name) if ffmpeg_dir else shutil.which("ffmpeg")
        if not ffmpeg:
            return {"available": False, "suspicious": False, "reason": "ffmpeg indisponivel"}
        sample_rate = 44100
        completed = subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-t",
                str(max(5, YTDLP_SPECTRAL_SECONDS)),
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "-f",
                "f32le",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(90, YTDLP_SPECTRAL_SECONDS * 3),
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            return {"available": False, "suspicious": False, "reason": detail[-300:] or "ffmpeg falhou"}
        samples = np.frombuffer(completed.stdout, dtype="<f4")
        if samples is None or len(samples) < sample_rate:
            return {"available": False, "suspicious": False, "reason": "audio curto demais"}
        n_fft = 4096
        hop_length = 2048
        frames = np.lib.stride_tricks.sliding_window_view(samples, n_fft)[::hop_length]
        if frames.size == 0:
            return {"available": False, "suspicious": False, "reason": "espectro vazio"}
        window = np.hanning(n_fft)
        magnitude = np.abs(np.fft.rfft(frames * window, axis=1))
        peak_magnitude = np.percentile(magnitude, 90, axis=0)
        frequencies = np.fft.rfftfreq(n_fft, d=1.0 / sample_rate)
        return evaluate_spectral_profile(frequencies, peak_magnitude)
    except Exception as exc:
        return {"available": False, "suspicious": False, "reason": str(exc)}


def spectral_profile_score(profile: Dict[str, Any]) -> float:
    cutoff = _finite_float(profile.get("cutoff_hz")) or 0.0
    drop = _finite_float(profile.get("drop_db"))
    return cutoff + (drop if drop is not None else -100.0)


def _best_word_similarity(target_word: str, candidate_words: List[str]) -> float:
    if not target_word or not candidate_words:
        return 0.0
    return max(SequenceMatcher(None, target_word, word).ratio() for word in candidate_words)


def _contains_normalized_phrase(text: str, phrase: str) -> bool:
    pattern = r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b"
    return re.search(pattern, text) is not None


def _youtube_variant_penalty(candidate_text: str, requested_title: str) -> int:
    requested = normalize_loose(requested_title)
    markers = {
        "karaoke": 100,
        "cover": 80,
        "nightcore": 100,
        "slowed": 100,
        "sped up": 100,
        "bass boosted": 80,
        "8d": 80,
        "live": 45,
        "extended": 45,
        "remix": 35,
        "lyrics": 15,
    }
    return sum(
        value
        for marker, value in markers.items()
        if _contains_normalized_phrase(candidate_text, marker) and not _contains_normalized_phrase(requested, marker)
    )


def _youtube_official_score(entry: Dict[str, Any], artist: str) -> int:
    if not YTDLP_PREFER_OFFICIAL:
        return 0
    title = normalize_loose(entry.get("title") or "")
    channel = normalize_loose(" ".join(str(entry.get(key) or "") for key in ("uploader", "channel", "uploader_id", "channel_id")))
    artist_key = normalize_loose(artist)
    score = 0
    if title.find("official audio") >= 0:
        score += 60
    elif title.find("official music video") >= 0 or title.find("official video") >= 0:
        score += 45
    elif "official" in title:
        score += 25
    if channel.endswith(" topic") or " topic " in f" {channel} ":
        score += 80
    if "vevo" in channel:
        score += 35
    if entry.get("channel_is_verified") or entry.get("uploader_is_verified"):
        score += 50
    if artist_key and channel and (artist_key in channel or channel in artist_key):
        score += 25
    return score


def score_youtube_entry(entry: Dict[str, Any], artist: str, title: str) -> int:
    candidate_title = normalize_loose(entry.get("title") or "")
    text = normalize_loose(" ".join(str(entry.get(k) or "") for k in ("title", "uploader", "channel")))
    artist_key = normalize_loose(artist)
    title_key = normalize_loose(title)
    score = 0
    if title_key and title_key in candidate_title:
        score += 100
    for word in title_key.split():
        if len(word) > 2 and word in candidate_title:
            score += 8
    if title_key and title_key not in candidate_title:
        candidate_words = [word for word in candidate_title.split() if len(word) > 2]
        similarities = [_best_word_similarity(word, candidate_words) for word in title_key.split() if len(word) > 2]
        if similarities and min(similarities) >= 0.72:
            score += round(80 * sum(similarities) / len(similarities))
    first_artist = normalize_loose(re.split(r",|&| feat\\.? | ft\\.? ", artist, maxsplit=1, flags=re.I)[0])
    if first_artist and first_artist in text:
        score += 40
    for word in artist_key.split():
        if len(word) > 2 and word in text:
            score += 4
    duration = entry.get("duration")
    if isinstance(duration, (int, float)) and 90 <= duration <= 900:
        score += 10
    score += _youtube_official_score(entry, artist)
    score -= _youtube_variant_penalty(text, title)
    bitrate = youtube_audio_bitrate_kbps(entry)
    if bitrate is not None:
        score += min(35, round(bitrate / 5))
    return score


def choose_youtube_candidates(
    ydl: yt_dlp.YoutubeDL,
    queries: List[str],
    artist: str,
    title: str,
    inspect_formats: bool = False,
) -> List[Dict[str, Any]]:
    search_count = max(1, YTDLP_SEARCH_RESULTS)
    candidates: Dict[str, Dict[str, Any]] = {}
    for query in queries:
        try:
            info = ydl.extract_info(f"ytsearch{search_count}:{query}", download=False)
        except Exception as exc:
            debug(f"Falha na consulta do YouTube '{query}': {exc}")
            continue
        for raw_entry in (info or {}).get("entries") or []:
            if not isinstance(raw_entry, dict):
                continue
            url = _youtube_entry_url(raw_entry)
            if not url:
                continue
            current = candidates.get(url)
            if current is None or len(raw_entry.get("formats") or []) > len(current.get("formats") or []):
                candidates[url] = dict(raw_entry)

    ranked = list(candidates.values())
    for entry in ranked:
        entry["_imd_score"] = score_youtube_entry(entry, artist, title)
    ranked.sort(
        key=lambda item: (
            int(item.get("_imd_score") or 0),
            int(item.get("view_count") or 0),
        ),
        reverse=True,
    )
    ranked = ranked[:max(1, YTDLP_CANDIDATE_LIMIT)]

    if inspect_formats:
        hydrated: List[Dict[str, Any]] = []
        for entry in ranked:
            if _youtube_audio_formats(entry):
                hydrated.append(entry)
                continue
            url = _youtube_entry_url(entry)
            try:
                full_entry = ydl.extract_info(url, download=False) if url else None
            except Exception as exc:
                debug(f"Falha ao inspecionar formatos de {url}: {exc}")
                full_entry = None
            if isinstance(full_entry, dict):
                merged = dict(entry)
                merged.update(full_entry)
                hydrated.append(merged)
            else:
                hydrated.append(entry)
        ranked = hydrated

    for entry in ranked:
        entry["_imd_score"] = score_youtube_entry(entry, artist, title)
    ranked.sort(
        key=lambda item: (
            youtube_source_quality_tier(item),
            int(item.get("_imd_score") or 0),
            youtube_audio_bitrate_kbps(item) or 0.0,
            int(item.get("view_count") or 0),
        ),
        reverse=True,
    )
    return ranked


def choose_youtube_url(ydl: yt_dlp.YoutubeDL, query: str, artist: str, title: str) -> Optional[str]:
    entries = choose_youtube_candidates(ydl, [query], artist, title)
    if not entries:
        return None
    return _youtube_entry_url(entries[0])

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
    selected_url = ""
    quality_fallback: Optional[Dict[str, Any]] = None
    quality_token = hashlib.sha1(f"{tid}|{datetime.now().isoformat()}".encode("utf-8")).hexdigest()[:12]

    def remember_quality_fallback(path: str, profile: Dict[str, Any], url: str, position: int) -> None:
        nonlocal quality_fallback
        source = Path(path)
        target = source
        stash = Path(folder) / f".imd-quality-{quality_token}-{position}{source.suffix}"
        new_score = spectral_profile_score(profile)
        if quality_fallback and new_score <= float(quality_fallback["score"]):
            source.unlink(missing_ok=True)
            return
        if quality_fallback:
            Path(str(quality_fallback["stash"])).unlink(missing_ok=True)
        os.replace(source, stash)
        quality_fallback = {
            "stash": str(stash),
            "target": str(target),
            "profile": profile,
            "score": new_score,
            "url": url,
        }

    cookie_attempts = [not YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN]
    if cookie_attempts[0] and YTDLP_COOKIES_FROM_BROWSER and YTDLP_COOKIES_FROM_BROWSER.lower() not in ("0", "none", "off", "false", "no"):
        cookie_attempts.append(False)

    for use_browser_cookies in cookie_attempts:
        try:
            if not use_browser_cookies:
                log("Tentando busca e download sem cookies do navegador.")
            with yt_dlp.YoutubeDL(yt_dlp_opts(folder, base, use_browser_cookies=use_browser_cookies)) as ydl:
                candidates = choose_youtube_candidates(ydl, queries, artist, title, inspect_formats=True)
                if not candidates:
                    last_error = "no youtube search results"
                    continue
                attempt_limit = min(len(candidates), max(1, YTDLP_DOWNLOAD_ATTEMPTS))
                log(f"YouTube: {len(candidates)} candidato(s) comparado(s); ate {attempt_limit} tentativa(s) de download.")
                for position, candidate in enumerate(candidates[:attempt_limit], start=1):
                    selected_url = _youtube_entry_url(candidate)
                    candidate_title = str(candidate.get("title") or "sem titulo").strip()
                    candidate_channel = str(candidate.get("channel") or candidate.get("uploader") or "canal desconhecido").strip()
                    source_description = youtube_source_description(candidate)
                    score = int(candidate.get("_imd_score") or 0)
                    log(
                        f"YouTube candidato {position}/{attempt_limit}: {candidate_title} | "
                        f"canal={candidate_channel} | {source_description} | score={score}"
                    )
                    source_bitrate = youtube_audio_bitrate_kbps(candidate)
                    if source_bitrate is not None and source_bitrate < max(1, YTDLP_MIN_SOURCE_BITRATE_KBPS):
                        log(
                            f"Aviso: fonte estimada em ~{source_bitrate:.0f} kbps, abaixo do minimo preferido "
                            f"de {YTDLP_MIN_SOURCE_BITRATE_KBPS} kbps."
                        )
                    try:
                        download_result = ydl.download([selected_url])
                        if download_result not in (None, 0):
                            last_error = f"yt-dlp return code {download_result}"
                            log_error(f"[YOUTUBE] Candidato falhou: {selected_url} :: {last_error}")
                            continue

                        final_path = find_downloaded_file(folder, base, preferred_ext=preferred_ext)
                        if AUDIO_FORMAT == "mp3" and (not final_path or Path(final_path).suffix.lower() != ".mp3"):
                            downloaded_path = find_downloaded_file(folder, base)
                            if downloaded_path:
                                final_path = convert_existing_to_mp3(downloaded_path)
                        if final_path and os.path.exists(final_path):
                            spectral_profile = inspect_downloaded_spectrum(final_path)
                            if spectral_profile.get("available"):
                                cutoff_hz = _finite_float(spectral_profile.get("cutoff_hz")) or 0.0
                                drop_db = _finite_float(spectral_profile.get("drop_db"))
                                if spectral_profile.get("suspicious"):
                                    log(
                                        f"Corte espectral suspeito perto de {cutoff_hz / 1000:.1f} kHz"
                                        + (f" (queda de {abs(drop_db):.1f} dB)." if drop_db is not None else ".")
                                    )
                                    remember_quality_fallback(final_path, spectral_profile, selected_url, position)
                                    final_path = None
                                    if position < attempt_limit:
                                        log("Tentando automaticamente o proximo candidato do YouTube.")
                                    continue
                                log(f"Espectro verificado: alcance aproximado de {cutoff_hz / 1000:.1f} kHz, sem corte rigido suspeito.")
                            elif YTDLP_SPECTRAL_CHECK:
                                debug(f"Verificacao espectral indisponivel: {spectral_profile.get('reason') or 'motivo desconhecido'}")
                                if quality_fallback:
                                    Path(final_path).unlink(missing_ok=True)
                                    final_path = None
                                    continue
                            if quality_fallback:
                                Path(str(quality_fallback["stash"])).unlink(missing_ok=True)
                                quality_fallback = None
                            log(f"YouTube selecionado: {selected_url}")
                            break
                        last_error = "file not found after download"
                    except Exception as exc:
                        last_error = str(exc)
                        log_error(f"[YOUTUBE] Candidato falhou: {selected_url} :: {exc}")
                        if use_browser_cookies and "cookie" in last_error.lower():
                            YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN = True
                            log("Cookies do navegador falharam; desativando cookies para o restante desta execucao.")
                            break
                if final_path and os.path.exists(final_path):
                    break
        except Exception as e:
            last_error = str(e)
            log_error(f"[YOUTUBE] Falha na busca de candidatos: {artist} - {title} :: {e}")
            if use_browser_cookies and "cookie" in last_error.lower():
                YTDLP_BROWSER_COOKIES_DISABLED_FOR_RUN = True
                log("Cookies do navegador falharam; desativando cookies para o restante desta execucao.")

        if (final_path and os.path.exists(final_path)) or quality_fallback:
            break

    if (not final_path or not os.path.exists(final_path)) and quality_fallback:
        fallback_stash = str(quality_fallback["stash"])
        fallback_target = str(quality_fallback["target"])
        os.replace(fallback_stash, fallback_target)
        final_path = fallback_target
        selected_url = str(quality_fallback["url"])
        fallback_cutoff = (_finite_float(quality_fallback["profile"].get("cutoff_hz")) or 0.0) / 1000
        log(
            f"Todas as fontes testadas apresentaram limitacoes; mantendo a melhor alternativa "
            f"(alcance aproximado de {fallback_cutoff:.1f} kHz)."
        )

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
        log_error(f"[YOUTUBE] Post-process exception: {selected_url or f'{artist} - {title}'} :: {e}")
        return "failed", None

# =========================
# Spotify via public embed __NEXT_DATA__
# =========================
def spotify_embed_http_get_text(url: str, timeout: int = 20) -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://open.spotify.com/",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        # A build empacotada pelo PyInstaller nao herda necessariamente o
        # repositorio de certificados do Windows. Use explicitamente o bundle
        # mantido pelo certifi, que tambem e incluido na distribuicao.
        ssl_context = (
            ssl._create_unverified_context()
            if DISABLE_SSL_VERIFY
            else ssl.create_default_context(cafile=certifi.where())
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        message = f"[SPOTIFY_EMBED] HTTP error {url} :: {e}"
        log_error(message)
        log(message)
        return None

def spotify_public_html_candidates(entity_type: str, entity_id: str) -> List[str]:
    return [
        f"https://open.spotify.com/embed/{entity_type}/{entity_id}",
        f"https://open.spotify.com/embed/{entity_type}/{entity_id}?utm_source=generator",
        f"https://open.spotify.com/{entity_type}/{entity_id}",
    ]

def spotify_fetch_public_html(entity_type: str, entity_id: str, timeout: int = 20) -> Tuple[str, Optional[str]]:
    last_url = ""
    for url in spotify_public_html_candidates(entity_type, entity_id):
        last_url = url
        log(f"🌐 Lendo {entity_type} do Spotify: {url}")
        html_text = spotify_embed_http_get_text(url, timeout=timeout)
        if html_text:
            log(f"Spotify HTML recebido: {len(html_text)} bytes de {url}")
            return url, html_text
    return last_url, None

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
        title = normalize_spotify_text(item.get("title") or "")
        artist = normalize_spotify_text(item.get("subtitle") or item.get("artist") or "")
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

def normalize_spotify_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<.*?>", "", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def spotify_parse_tracklist_deep(next_data: Dict[str, Any]) -> Dict[str, Any]:
    tracks: List[Dict[str, str]] = []
    seen = set()
    entity_name = ""

    def add_track(title: str, artist: str, album: str = "") -> None:
        title = normalize_spotify_text(title)
        artist = normalize_spotify_text(artist)
        album = normalize_spotify_text(album)
        key = (normalize_loose(artist), normalize_loose(title))
        if artist and title and key not in seen:
            seen.add(key)
            tracks.append({"artist": artist, "title": title, "album": album})

    def artist_names(value: Any) -> str:
        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    name = normalize_spotify_text(item.get("name") or item.get("title") or "")
                    if name:
                        names.append(name)
                elif isinstance(item, str) and item.strip():
                    names.append(normalize_spotify_text(item))
            return ", ".join(names)
        if isinstance(value, str):
            return value.strip()
        return ""

    def walk(value: Any) -> None:
        nonlocal entity_name
        if isinstance(value, dict):
            if not entity_name:
                entity_name = str(value.get("name") or value.get("title") or "").strip()

            title = normalize_spotify_text(value.get("name") or value.get("title") or "")
            artist = (
                artist_names(value.get("artists"))
                or artist_names(value.get("artist"))
                or normalize_spotify_text(value.get("subtitle") or "")
            )
            album = ""
            if isinstance(value.get("album"), dict):
                album = normalize_spotify_text(value["album"].get("name") or value["album"].get("title") or "")
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
        title = normalize_spotify_text(m.group(1))
        artist = normalize_spotify_text(m.group(2))
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

def spotify_embed_fetch_collection(url: str, force_refresh: bool = False, write_cache: bool = True) -> Optional[Dict[str, Any]]:
    norm_url = normalize_spotify_url(url)
    entity_type = spotify_detect_entity_type(norm_url)
    entity_id = spotify_extract_entity_id(norm_url, entity_type)
    if not entity_id or entity_type not in SPOTIFY_ENTITY_TYPES:
        log_error(f"[SPOTIFY_EMBED] Invalid Spotify URL: {url}")
        return None

    cache = load_embed_cache()
    cached = cache.get(norm_url)
    if not force_refresh and cached and isinstance(cached, dict) and cached.get("tracks"):
        cached.setdefault(
            "partial_possible",
            entity_type == "playlist" and len(cached.get("tracks") or []) >= 50,
        )
        log(f"🗂️ Usando cache do embed Spotify: {norm_url}")
        return cached
    if force_refresh and cached:
        log(f"🔄 Reescan ativo: ignorando cache do embed Spotify: {norm_url}")

    embed_url, html_text = spotify_fetch_public_html(entity_type, entity_id, timeout=SPOTIFY_EMBED_TIMEOUT_SECONDS)
    if not html_text:
        log_error(f"[SPOTIFY_EMBED] Nenhum HTML recebido do Spotify: {norm_url}")
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
        log(f"Spotify parse __NEXT_DATA__: tracks={0 if not parsed else len(parsed.get('tracks') or [])}")
    else:
        log_error(f"[SPOTIFY_EMBED] __NEXT_DATA__ nao encontrado em {embed_url}")

    if not parsed or not parsed.get("tracks"):
        parsed = spotify_parse_embed_tracklist_from_html(html_text)
        log(f"Spotify parse HTML fallback: tracks={len(parsed.get('tracks') or [])}")

    if not parsed.get("tracks"):
        log_error(f"[SPOTIFY_EMBED] trackList empty: {embed_url} | html_bytes={len(html_text)}")
        return None

    result = {
        "url": norm_url,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "name": parsed.get("name", ""),
        "uri": parsed.get("uri", ""),
        "tracks": parsed.get("tracks", []),
        "count": parsed.get("count", 0),
        "partial_possible": entity_type == "playlist" and int(parsed.get("count", 0) or 0) >= 50,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": "spotify_embed",
    }
    if write_cache:
        cache[norm_url] = result
        save_embed_cache(cache)
    if result["partial_possible"]:
        log("Aviso: o embed publico mostrou 50 ou mais faixas; a playlist pode ter mais itens fora dessa pagina.")
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
    partial_possible = bool(collection.get("partial_possible"))
    if not dry_run and not partial_possible and (count_failed == 0 or can_mark_done_with_failures):
        hist.add(pid)
    elif partial_possible:
        log("Playlist nao marcada como concluida porque o embed publico pode estar incompleto.")
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
    ensure_runtime_dirs()
    parser = argparse.ArgumentParser(description="Spotify embed playlist index + yt-dlp downloader")
    parser.add_argument("--tagmusic", dest="tagmusic", action=argparse.BooleanOptionalAction, default=None, help="Ignora downloads e aplica tags basicas em MUSIC_DIR")
    parser.add_argument("--tag-force", dest="tag_force", action=argparse.BooleanOptionalAction, default=None, help="Sobrescreve tags existentes no modo --tagmusic")
    parser.add_argument("--reescan-list", dest="reescan_list", action=argparse.BooleanOptionalAction, default=None, help="Para playlists/artistas do Spotify, verifica a pasta e baixa so faixas novas")
    parser.add_argument("--dry-run", dest="dry_run", action=argparse.BooleanOptionalAction, default=None, help="Mostra o que faria, mas nao baixa musicas nem grava historico")
    parser.add_argument("--only-row", type=int, default=None, help="Processa apenas uma linha da planilha (1-based)")
    parser.add_argument("--row-selection", default=None, help="Processa linhas e intervalos: 2,5,8-12 ou todos")
    parser.add_argument("--only-url", default=None, help="Processa apenas uma URL Spotify informada")
    parser.add_argument("--input-file", default=None, help="CSV local para processar no lugar da planilha do config")
    parser.add_argument("--conversion-only", dest="conversion_only", action=argparse.BooleanOptionalAction, default=None, help="Executa apenas a conversao de arquivos de audio")
    args, _ = parser.parse_known_args()
    reescan_list = config_bool("execution.reescan_list", False) if args.reescan_list is None else args.reescan_list
    dry_run = config_bool("execution.dry_run", False) if args.dry_run is None else args.dry_run
    tagmusic = config_bool("execution.tagmusic", False) if args.tagmusic is None else args.tagmusic
    tag_force = config_bool("execution.tag_force", False) if args.tag_force is None else args.tag_force
    only_row = args.only_row if args.only_row is not None else config_value("execution.only_row")
    row_selection = str(args.row_selection or "").strip()
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

    if AUDIO_FORMAT == "mp3" and not bundled_ffmpeg_dir():
        raise RuntimeError("audio.format=mp3 precisa do ffmpeg/ffprobe. Reinstale o IMD ou instale o FFmpeg no sistema.")

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
    elif row_selection:
        selected_rows = parse_row_selection(row_selection, total_rows=len(df))
        if selected_rows is not None:
            df = df.iloc[[row_number - 1 for row_number in selected_rows]]
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
