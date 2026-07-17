import argparse
import cgi
import csv
import json
import mimetypes
import re
import shutil
import ssl
import subprocess
import sys
import threading
import uuid
from io import BytesIO, StringIO
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse
import urllib.request
import urllib.error

import yaml
import pandas as pd
import requests


def app_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_root_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(str(bundle_dir)).resolve()
    return app_root_dir()


ROOT_DIR = app_root_dir()
RESOURCE_DIR = resource_root_dir()
WEB_DIR = RESOURCE_DIR / "web"
CONFIG_FILE = ROOT_DIR / "config.yaml"
SAMPLE_CONFIG_FILE = RESOURCE_DIR / "config.sample.yaml"
BACKUP_DIR = ROOT_DIR / "config_backups"
SCRIPT_FILE = ROOT_DIR / "music_downloader.py"
IMPORT_DIR = ROOT_DIR / "imports"
TASK_DIR = ROOT_DIR / "tasks"
TASK_LOCK = threading.Lock()
TASKS: Dict[str, "BackgroundTask"] = {}
IMPORTS: Dict[str, Dict[str, Any]] = {}


def worker_command(*args: str) -> List[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--worker", *args]
    return [sys.executable, str(SCRIPT_FILE), *args]


@dataclass
class BackgroundTask:
    id: str
    kind: str
    command: List[str]
    status: str = "pending"
    returncode: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    logs: deque[str] = field(default_factory=lambda: deque(maxlen=1200))
    progress: Dict[str, Any] = field(default_factory=dict)
    process: subprocess.Popen | None = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "returncode": self.returncode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "logs": list(self.logs),
            "progress": self.progress,
        }

    @classmethod
    def from_snapshot(cls, data: Dict[str, Any]) -> "BackgroundTask":
        task = cls(
            id=str(data.get("id")),
            kind=str(data.get("kind") or "unknown"),
            command=[str(x) for x in data.get("command") or []],
            status=str(data.get("status") or "unknown"),
            returncode=data.get("returncode"),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
        )
        task.logs.extend(str(x) for x in data.get("logs") or [])
        task.progress = data.get("progress") or {}
        return task


def read_yaml_file(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} precisa conter um mapa de configuracao.")
    return data


def write_yaml_file(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=False, default_flow_style=False)


def flatten_config_paths(data: Dict[str, Any], prefix: str = "") -> List[str]:
    paths: List[str] = []
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            paths.extend(flatten_config_paths(value, dotted))
        else:
            paths.append(dotted)
    return paths


def validate_config_data(config: Dict[str, Any], sample: Dict[str, Any]) -> Tuple[bool, List[str]]:
    messages: List[str] = []
    deprecated_paths = {
        "spotify.credentials_file",
        "spotify.client_id",
        "spotify.client_secret",
    }
    config_paths = set(flatten_config_paths(config))
    sample_paths = set(flatten_config_paths(sample))
    missing_in_config = sorted(sample_paths - config_paths)
    missing_in_sample = sorted((config_paths - sample_paths) - deprecated_paths)

    if missing_in_config:
        messages.append("Campos ausentes no config.yaml: " + ", ".join(missing_in_config))
    if missing_in_sample:
        messages.append("Campos ausentes no config.sample.yaml: " + ", ".join(missing_in_sample))
    if not messages:
        messages.append("Config carregado com sucesso.")
    return not missing_in_config and not missing_in_sample, messages


def validate_config_files() -> Tuple[bool, List[str]]:
    try:
        config = read_yaml_file(CONFIG_FILE)
    except Exception as e:
        return False, [f"config.yaml invalido: {e}"]

    try:
        sample = read_yaml_file(SAMPLE_CONFIG_FILE)
    except Exception as e:
        return False, [f"config.sample.yaml invalido: {e}"]

    return validate_config_data(config, sample)


def backup_config_file() -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"config_{stamp}.yaml"
    shutil.copy2(CONFIG_FILE, backup_path)
    return backup_path


def save_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config, dict):
        raise ValueError("Config recebido precisa ser um objeto.")
    sample = read_yaml_file(SAMPLE_CONFIG_FILE)
    valid, messages = validate_config_data(config, sample)
    if not valid:
        return {"ok": False, "validation": {"ok": False, "messages": messages}}

    backup_path = backup_config_file()
    write_yaml_file(CONFIG_FILE, config)
    data = load_dashboard_data()
    data["backup"] = str(backup_path)
    return data


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def task_file(task_id: str) -> Path:
    return TASK_DIR / f"{task_id}.json"


def persist_task(task: BackgroundTask) -> None:
    TASK_DIR.mkdir(exist_ok=True)
    payload = task.snapshot()
    payload["command"] = task.command
    task_file(task.id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_persisted_tasks() -> None:
    if not TASK_DIR.exists():
        return
    with TASK_LOCK:
        for path in TASK_DIR.glob("*.json"):
            try:
                task = BackgroundTask.from_snapshot(json.loads(path.read_text(encoding="utf-8")))
                TASKS.setdefault(task.id, task)
            except Exception:
                continue


def update_task_progress_from_line(task: BackgroundTask, line: str) -> None:
    if "Conversao:" in line and "arquivos=" in line:
        match = re.search(r"arquivos=(\d+)", line)
        if match:
            task.progress["total"] = int(match.group(1))
            task.progress["phase"] = "conversion"
    if "Conversao concluida:" in line:
        for key, label in (("converted", "convertidos"), ("existing", "existentes"), ("dry_run", "dry_run"), ("failed", "falhas")):
            match = re.search(label + r"=(\d+)", line)
            if match:
                task.progress[key] = int(match.group(1))
        task.progress["done"] = True
    if "Resumo:" in line:
        for key, label in (("rows", "linhas"), ("playlists", "playlists"), ("artists", "artistas"), ("new", "novas"), ("existing", "existentes"), ("failed", "falhas")):
            match = re.search(label + r"=(\d+)", line)
            if match:
                task.progress[key] = int(match.group(1))
        task.progress["done"] = True


def start_background_task(kind: str, command: List[str]) -> BackgroundTask:
    task = BackgroundTask(id=str(uuid.uuid4()), kind=kind, command=command)
    with TASK_LOCK:
        TASKS[task.id] = task
    persist_task(task)

    thread = threading.Thread(target=run_background_task, args=(task,), daemon=True)
    thread.start()
    return task


def run_background_task(task: BackgroundTask) -> None:
    task.status = "running"
    task.started_at = now_iso()
    task.logs.append("Iniciando tarefa: " + " ".join(task.command))
    persist_task(task)
    try:
        process = subprocess.Popen(
            task.command,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        task.process = process
        assert process.stdout is not None
        for line in process.stdout:
            clean_line = line.rstrip()
            task.logs.append(clean_line)
            update_task_progress_from_line(task, clean_line)
            persist_task(task)
        task.returncode = process.wait()
        if task.status == "canceling":
            task.status = "canceled"
        elif task.returncode == 0:
            task.status = "succeeded"
        else:
            task.status = "failed"
            task.logs.append(f"Tarefa terminou com codigo {task.returncode}.")
    except Exception as e:
        task.status = "failed"
        task.logs.append(f"Falha ao executar tarefa: {e}")
    finally:
        task.finished_at = now_iso()
        task.process = None
        persist_task(task)


def latest_task(kind: str) -> BackgroundTask | None:
    with TASK_LOCK:
        matching = [task for task in TASKS.values() if task.kind == kind]
    if not matching:
        return None
    return sorted(matching, key=lambda task: task.started_at or "", reverse=True)[0]


def all_tasks_payload() -> Dict[str, Any]:
    with TASK_LOCK:
        tasks = [task.snapshot() for task in TASKS.values()]
    tasks.sort(key=lambda task: task.get("started_at") or "", reverse=True)
    return {"ok": True, "tasks": tasks}


def config_state_dir() -> Path:
    config = read_yaml_file(CONFIG_FILE)
    paths = config.get("paths", {}) if isinstance(config.get("paths"), dict) else {}
    return Path(str(paths.get("state_dir") or ROOT_DIR))


def read_text_lines(path: Path, limit: int = 300) -> List[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def load_history_payload() -> Dict[str, Any]:
    state_dir = config_state_dir()
    files = {
        "baixados": state_dir / "baixados.txt",
        "erros": state_dir / "erros.txt",
        "failed_items": state_dir / "failed_items.jsonl",
        "tracks": state_dir / "tracks_history.txt",
        "spotify": state_dir / "spotify_history.txt",
        "files": state_dir / "files_history.txt",
    }
    data = {name: read_text_lines(path) for name, path in files.items()}
    return {
        "ok": True,
        "state_dir": str(state_dir),
        "counts": {name: len(lines) for name, lines in data.items()},
        "files": data,
    }


def failure_lines_to_rows(lines: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in lines:
        text = line.split("] ", 1)[1] if "] " in line else line
        candidate = ""
        for marker in ("File not found after download:", "Exception:", "Post-process exception:"):
            if marker in text:
                candidate = text.split(marker, 1)[1].split("::", 1)[0].strip()
                break
        if not candidate:
            continue
        if " - " in candidate:
            artist, title = candidate.split(" - ", 1)
            rows.append({"Artista": artist.strip(), "Musica": title.strip()})
        else:
            rows.append({"Musica": candidate})

    unique: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = f"{row.get('Artista', '')}|{row.get('Musica', '')}".lower()
        unique[key] = row
    return list(unique.values())


def environment_payload() -> Dict[str, Any]:
    config = read_yaml_file(CONFIG_FILE)
    paths = config.get("paths", {}) if isinstance(config.get("paths"), dict) else {}
    source = config.get("source", {}) if isinstance(config.get("source"), dict) else {}
    checks = [
        {"name": "Python", "ok": True, "detail": sys.version.split()[0]},
        {"name": "ffmpeg", "ok": bool(shutil.which("ffmpeg")), "detail": shutil.which("ffmpeg") or "nao encontrado"},
        {"name": "yt-dlp", "ok": True, "detail": "importado"},
        {"name": "pandas", "ok": True, "detail": pd.__version__},
        {"name": "config.yaml", "ok": CONFIG_FILE.exists(), "detail": str(CONFIG_FILE)},
        {"name": "Pasta de musicas", "ok": Path(str(paths.get("music_dir") or "")).exists(), "detail": str(paths.get("music_dir") or "")},
        {"name": "Pasta de estado", "ok": Path(str(paths.get("state_dir") or "")).exists(), "detail": str(paths.get("state_dir") or "")},
        {"name": "Google Sheets URL", "ok": bool(source.get("google_sheet_csv")), "detail": str(source.get("google_sheet_csv") or "")},
    ]
    return {"ok": True, "checks": checks}


def spotify_check_payload(url: str) -> Dict[str, Any]:
    url = str(url or "").strip()
    if not url:
        return {"ok": False, "error": "Informe um link do Spotify."}
    try:
        import music_downloader

        collection = music_downloader.spotify_embed_fetch_collection(url, force_refresh=True, write_cache=False)
        if not collection or not collection.get("tracks"):
            return {
                "ok": False,
                "error": "Nao foi possivel extrair musicas desse link.",
                "url": music_downloader.normalize_spotify_url(url),
            }
        return {
            "ok": True,
            "url": collection.get("url"),
            "name": collection.get("name") or "",
            "entity_type": collection.get("entity_type") or "",
            "count": len(collection.get("tracks") or []),
            "sample": (collection.get("tracks") or [])[:5],
        }
    except Exception as e:
        return {"ok": False, "error": format_error(e), "url": url}


def start_conversion_task() -> Dict[str, Any]:
    current = latest_task("conversion")
    if current and current.status in ("pending", "running", "canceling"):
        return {"ok": False, "error": "Ja existe uma conversao em andamento.", "task": current.snapshot()}

    command = worker_command("--conversion-only")
    task = start_background_task("conversion", command)
    return {"ok": True, "task": task.snapshot()}


def start_download_task(options: Dict[str, Any]) -> Dict[str, Any]:
    current = latest_task("download")
    if current and current.status in ("pending", "running", "canceling"):
        return {"ok": False, "error": "Ja existe um download em andamento.", "task": current.snapshot()}

    command = worker_command()
    if options.get("reescan_list"):
        command.append("--reescan-list")
    else:
        command.append("--no-reescan-list")
    if options.get("dry_run"):
        command.append("--dry-run")
    else:
        command.append("--no-dry-run")

    only_row = options.get("only_row")
    if only_row not in (None, ""):
        command += ["--only-row", str(int(only_row))]

    only_url = str(options.get("only_url") or "").strip()
    if only_url:
        command += ["--only-url", only_url]

    if options.get("tagmusic") is not None:
        command.append("--tagmusic" if options.get("tagmusic") else "--no-tagmusic")

    task = start_background_task("download", command)
    return {"ok": True, "task": task.snapshot()}


def normalize_rows_for_import(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [normalize_import_row(row, index) for index, row in enumerate(rows)]


def validate_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = normalize_rows_for_import(rows)
    issues: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}
    for row in normalized:
        key = "|".join([row.get("artist", "").lower(), row.get("title", "").lower(), row.get("spotify_url", "").lower()])
        if key.strip("|"):
            if key in seen:
                issues.append({"row_number": row["row_number"], "severity": "warning", "message": f"Possivel duplicada da linha {seen[key]}."})
            else:
                seen[key] = row["row_number"]
        if row["type"] == "empty":
            issues.append({"row_number": row["row_number"], "severity": "error", "message": "Linha sem artista/musica e sem URL Spotify."})
        if row.get("spotify_url") and "open.spotify.com/" not in row["spotify_url"]:
            issues.append({"row_number": row["row_number"], "severity": "error", "message": "URL Spotify parece invalida."})
        if row["type"] == "manual" and not row.get("genre"):
            issues.append({"row_number": row["row_number"], "severity": "warning", "message": "Genero vazio."})
    return {"ok": True, "counts": {"rows": len(normalized), "issues": len(issues)}, "issues": issues, "rows": normalized[:500]}


def start_rows_download_task(rows: List[Dict[str, Any]], options: Dict[str, Any]) -> Dict[str, Any]:
    if not rows:
        return {"ok": False, "error": "Nenhuma linha selecionada."}
    import_id = str(uuid.uuid4())
    normalized = normalize_rows_for_import(rows)
    csv_path = save_import_csv(import_id, normalized)
    IMPORTS[import_id] = {"filename": "selected_rows.csv", "csv_path": str(csv_path), "counts": {"total": len(normalized)}}
    return start_import_download_task(import_id, options)


def start_failure_retry_task(options: Dict[str, Any]) -> Dict[str, Any]:
    history = load_history_payload()
    rows = []
    for line in history["files"].get("failed_items", []):
        try:
            item = json.loads(line)
            rows.append(
                {
                    "Artista": item.get("artist", ""),
                    "Musica": item.get("title", ""),
                    "(opcional) Tag/Genero": item.get("genre", ""),
                    "Spotify Playlist (link)": item.get("spotify_url", ""),
                }
            )
        except Exception:
            continue
    rows = [row for row in rows if row.get("Spotify Playlist (link)") or row.get("Musica")]
    if not rows:
        rows = failure_lines_to_rows(history["files"].get("erros", []))
    if not rows:
        return {"ok": False, "error": "Nenhuma falha reaproveitavel encontrada em erros.txt."}
    return start_rows_download_task(rows, options)


def start_import_download_task(import_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
    current = latest_task("download")
    if current and current.status in ("pending", "running", "canceling"):
        return {"ok": False, "error": "Ja existe um download em andamento.", "task": current.snapshot()}

    imported = IMPORTS.get(import_id)
    csv_path = Path(imported["csv_path"]) if imported else IMPORT_DIR / f"{import_id}.csv"
    if not csv_path.exists():
        return {"ok": False, "error": "Importacao nao encontrada. Faca o preview do arquivo novamente."}

    command = worker_command("--input-file", str(csv_path))
    if options.get("reescan_list"):
        command.append("--reescan-list")
    else:
        command.append("--no-reescan-list")
    if options.get("dry_run"):
        command.append("--dry-run")
    else:
        command.append("--no-dry-run")
    if options.get("tagmusic") is not None:
        command.append("--tagmusic" if options.get("tagmusic") else "--no-tagmusic")

    task = start_background_task("download", command)
    return {"ok": True, "task": task.snapshot()}


def task_payload(task_id: str) -> Dict[str, Any]:
    with TASK_LOCK:
        task = TASKS.get(task_id)
    if not task:
        return {"ok": False, "error": "Tarefa nao encontrada."}
    return {"ok": True, "task": task.snapshot()}


def cancel_task(task_id: str) -> Dict[str, Any]:
    with TASK_LOCK:
        task = TASKS.get(task_id)
    if not task:
        return {"ok": False, "error": "Tarefa nao encontrada."}
    if task.status not in ("pending", "running"):
        return {"ok": True, "task": task.snapshot()}

    task.status = "canceling"
    task.logs.append("Cancelamento solicitado.")
    if task.process and task.process.poll() is None:
        task.process.terminate()
    return {"ok": True, "task": task.snapshot()}


def config_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    conversion = config.get("conversion", {}) if isinstance(config.get("conversion"), dict) else {}
    execution = config.get("execution", {}) if isinstance(config.get("execution"), dict) else {}
    paths = config.get("paths", {}) if isinstance(config.get("paths"), dict) else {}
    audio = config.get("audio", {}) if isinstance(config.get("audio"), dict) else {}
    source = config.get("source", {}) if isinstance(config.get("source"), dict) else {}

    return {
        "music_dir": paths.get("music_dir"),
        "state_dir": paths.get("state_dir"),
        "audio_format": audio.get("format"),
        "dry_run": execution.get("dry_run"),
        "reescan_list": execution.get("reescan_list"),
        "conversion_enabled": conversion.get("enable"),
        "conversion_only": conversion.get("conversion_only"),
        "conversion": f"{conversion.get('source_format')} -> {conversion.get('destination_format')}",
        "conversion_workers": conversion.get("workers"),
        "google_sheet_configured": bool(source.get("google_sheet_csv")),
    }


def load_dashboard_data() -> Dict[str, Any]:
    config = read_yaml_file(CONFIG_FILE)
    valid, messages = validate_config_files()
    return {
        "ok": True,
        "config": config,
        "summary": config_summary(config),
        "validation": {
            "ok": valid,
            "messages": messages,
        },
    }


def normalize_sheet_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def normalize_import_row(row: Dict[str, Any], index: int) -> Dict[str, Any]:
    clean = {str(key): normalize_sheet_value(value) for key, value in row.items()}
    spotify_url = clean.get("Spotify Playlist (link)", "") or clean.get("Spotify", "") or clean.get("URL", "") or clean.get("Url", "")
    artist = clean.get("Artista", "") or clean.get("Artist", "")
    title = clean.get("Musica", "") or clean.get("Música", "") or clean.get("Title", "") or clean.get("Track", "")
    genre = clean.get("(opcional) Tag/Genero", "") or clean.get("Genero", "") or clean.get("Gênero", "") or clean.get("Genre", "")
    row_type = classify_sheet_row(
        {
            "Spotify Playlist (link)": spotify_url,
            "Artista": artist,
            "Musica": title,
        }
    )
    return {
        "row_number": index + 1,
        "type": row_type,
        "artist": artist,
        "title": title,
        "genre": genre,
        "spotify_url": spotify_url,
        "raw": clean,
    }


def parse_txt_import(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, line in enumerate(text.splitlines()):
        value = line.strip()
        if not value:
            continue
        if "open.spotify.com/" in value:
            row = {"Spotify Playlist (link)": value}
        elif " - " in value:
            artist, title = value.split(" - ", 1)
            row = {"Artista": artist.strip(), "Musica": title.strip()}
        else:
            row = {"Musica": value}
        rows.append(normalize_import_row(row, len(rows)))
    return rows


def parse_import_file(filename: str, content: bytes) -> Dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        rows = parse_txt_import(content.decode("utf-8-sig"))
        columns = ["Artista", "Musica", "Spotify Playlist (link)"]
    elif suffix == ".csv":
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        columns = reader.fieldnames or []
        rows = [normalize_import_row(row, index) for index, row in enumerate(reader)]
    elif suffix == ".xlsx":
        df = pd.read_excel(BytesIO(content))
        df = df.fillna("")
        columns = [str(col) for col in df.columns]
        rows = [normalize_import_row(row.to_dict(), index) for index, row in df.iterrows()]
    else:
        raise ValueError("Formato nao suportado. Use txt, csv ou xlsx.")

    import_id = str(uuid.uuid4())
    csv_path = save_import_csv(import_id, rows)
    counts = {"total": len(rows), "playlist": 0, "artist": 0, "manual": 0, "empty": 0}
    for row in rows:
        counts[row["type"]] = counts.get(row["type"], 0) + 1
    IMPORTS[import_id] = {"filename": filename, "csv_path": str(csv_path), "counts": counts}
    return {
        "ok": True,
        "import_id": import_id,
        "filename": filename,
        "csv_path": str(csv_path),
        "columns": columns,
        "counts": counts,
        "rows": rows[:500],
        "truncated": len(rows) > 500,
    }


def save_import_csv(import_id: str, rows: List[Dict[str, Any]]) -> Path:
    IMPORT_DIR.mkdir(exist_ok=True)
    csv_path = IMPORT_DIR / f"{import_id}.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Artista", "Musica", "(opcional) Tag/Genero", "Spotify Playlist (link)"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "Artista": row.get("artist", ""),
                    "Musica": row.get("title", ""),
                    "(opcional) Tag/Genero": row.get("genre", ""),
                    "Spotify Playlist (link)": row.get("spotify_url", ""),
                }
            )
    return csv_path


def classify_sheet_row(row: Dict[str, str]) -> str:
    spotify_url = row.get("Spotify Playlist (link)", "") or row.get("Spotify", "") or row.get("URL", "")
    artist = row.get("Artista", "")
    title = row.get("Musica", "")
    if "open.spotify.com/playlist/" in spotify_url:
        return "playlist"
    if "open.spotify.com/artist/" in spotify_url:
        return "artist"
    if artist or title:
        return "manual"
    return "empty"


def read_sheet_dataframe(url_or_path: str, disable_ssl_verify: bool = False) -> pd.DataFrame:
    parsed = urlparse(str(url_or_path))
    if parsed.scheme in ("http", "https"):
        try:
            response = requests.get(
                url_or_path,
                timeout=30,
                verify=not disable_ssl_verify,
                headers={"User-Agent": "IMDLocal/0.1"},
            )
            response.raise_for_status()
            content = response.content.decode(response.encoding or "utf-8-sig")
        except requests.RequestException:
            context = ssl._create_unverified_context() if disable_ssl_verify else None
            with urllib.request.urlopen(url_or_path, timeout=30, context=context) as response:
                content = response.read().decode("utf-8-sig")
        return pd.read_csv(StringIO(content))
    return pd.read_csv(url_or_path)


def format_error(e: Exception) -> str:
    if isinstance(e, requests.RequestException):
        return str(e) or repr(e)
    if isinstance(e, urllib.error.URLError) and e.reason:
        return str(e.reason) or repr(e.reason)
    return str(e) or repr(e)


def load_sheet_preview(limit: int = 300) -> Dict[str, Any]:
    config = read_yaml_file(CONFIG_FILE)
    source = config.get("source", {}) if isinstance(config.get("source"), dict) else {}
    network = config.get("network", {}) if isinstance(config.get("network"), dict) else {}
    url = source.get("google_sheet_csv")
    if not url:
        return {"ok": False, "error": "source.google_sheet_csv nao esta configurado."}

    df = read_sheet_dataframe(str(url), bool(network.get("disable_ssl_verify")))
    df = df.fillna("")
    rows: List[Dict[str, Any]] = []
    counts = {"total": int(len(df)), "playlist": 0, "artist": 0, "manual": 0, "empty": 0}

    for index, raw_row in df.head(limit).iterrows():
        row = {str(key): normalize_sheet_value(value) for key, value in raw_row.to_dict().items()}
        row_type = classify_sheet_row(row)
        counts[row_type] = counts.get(row_type, 0) + 1
        rows.append(
            {
                "row_number": int(index) + 1,
                "type": row_type,
                "artist": row.get("Artista", ""),
                "title": row.get("Musica", ""),
                "genre": row.get("(opcional) Tag/Genero", ""),
                "spotify_url": row.get("Spotify Playlist (link)", "") or row.get("Spotify", "") or row.get("URL", ""),
                "raw": row,
            }
        )

    return {
        "ok": True,
        "limit": limit,
        "truncated": len(df) > limit,
        "columns": [str(col) for col in df.columns],
        "counts": counts,
        "rows": rows,
    }


class AppHandler(BaseHTTPRequestHandler):
    server_version = "IMDLocal/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "app": "imd-insane-music-downloader"})
            return
        if parsed.path == "/api/config":
            try:
                self.send_json(load_dashboard_data())
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=500)
            return
        if parsed.path.startswith("/api/tasks/"):
            task_id = parsed.path.rsplit("/", 1)[-1]
            payload = task_payload(task_id)
            self.send_json(payload, status=200 if payload.get("ok") else 404)
            return
        if parsed.path == "/api/conversion/latest":
            task = latest_task("conversion")
            self.send_json({"ok": True, "task": task.snapshot() if task else None})
            return
        if parsed.path == "/api/download/latest":
            task = latest_task("download")
            self.send_json({"ok": True, "task": task.snapshot() if task else None})
            return
        if parsed.path == "/api/tasks":
            self.send_json(all_tasks_payload())
            return
        if parsed.path == "/api/history":
            self.send_json(load_history_payload())
            return
        if parsed.path == "/api/environment":
            self.send_json(environment_payload())
            return
        if parsed.path == "/api/sheet/preview":
            try:
                self.send_json(load_sheet_preview())
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            try:
                payload = self.read_json_body()
                result = save_config(payload.get("config"))
                status = 200 if result.get("ok") else 400
                self.send_json(result, status=status)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=500)
            return
        if parsed.path == "/api/conversion/start":
            try:
                result = start_conversion_task()
                self.send_json(result, status=200 if result.get("ok") else 409)
            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, status=500)
            return
        if parsed.path == "/api/download/start":
            try:
                payload = self.read_json_body()
                result = start_download_task(payload.get("options") or {})
                self.send_json(result, status=200 if result.get("ok") else 409)
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        if parsed.path == "/api/spotify/check":
            try:
                payload = self.read_json_body()
                result = spotify_check_payload(str(payload.get("url") or ""))
                self.send_json(result, status=200 if result.get("ok") else 400)
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        if parsed.path == "/api/import/start":
            try:
                payload = self.read_json_body()
                result = start_import_download_task(str(payload.get("import_id") or ""), payload.get("options") or {})
                self.send_json(result, status=200 if result.get("ok") else 409)
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        if parsed.path == "/api/rows/start":
            try:
                payload = self.read_json_body()
                result = start_rows_download_task(payload.get("rows") or [], payload.get("options") or {})
                self.send_json(result, status=200 if result.get("ok") else 400)
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        if parsed.path == "/api/rows/validate":
            try:
                payload = self.read_json_body()
                self.send_json(validate_rows(payload.get("rows") or []))
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        if parsed.path == "/api/history/retry-failures":
            try:
                payload = self.read_json_body()
                result = start_failure_retry_task(payload.get("options") or {})
                self.send_json(result, status=200 if result.get("ok") else 400)
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=500)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/cancel"):
            task_id = parsed.path.split("/")[-2]
            result = cancel_task(task_id)
            self.send_json(result, status=200 if result.get("ok") else 404)
            return
        if parsed.path == "/api/import/preview":
            try:
                result = self.read_upload_preview()
                self.send_json(result)
            except Exception as e:
                self.send_json({"ok": False, "error": format_error(e)}, status=400)
            return
        self.send_error(404, "Endpoint nao encontrado")

    def read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw or "{}")
        if not isinstance(data, dict):
            raise ValueError("Corpo da requisicao precisa ser JSON objeto.")
        return data

    def read_upload_preview(self) -> Dict[str, Any]:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type"),
            },
        )
        file_item = form["file"] if "file" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            raise ValueError("Envie um arquivo no campo file.")
        content = file_item.file.read()
        return parse_import_file(file_item.filename, content)

    def serve_static(self, request_path: str) -> None:
        rel_path = request_path.lstrip("/") or "index.html"
        target = (WEB_DIR / rel_path).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())) or not target.is_file():
            self.send_error(404, "Arquivo nao encontrado")
            return

        content_type, _ = mimetypes.guess_type(str(target))
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    load_persisted_tasks()
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Painel local rodando em http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.", flush=True)
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel local do IMD Insane Music Downloader")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
