import os
import json
import hashlib
import shutil
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import date
from pathlib import Path


APP_NAME = "IMD Insane Music Downloader"
YT_DLP_WHEEL = "yt_dlp_latest.whl"
YT_DLP_META = "yt_dlp_update.json"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(str(bundle_dir)).resolve()
    return app_dir()


def update_dir(root: Path) -> Path:
    return root / "runtime_updates"


def yt_dlp_wheel_path(root: Path) -> Path:
    return update_dir(root) / YT_DLP_WHEEL


def yt_dlp_meta_path(root: Path) -> Path:
    return update_dir(root) / YT_DLP_META


def load_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
                return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=True, indent=2)


def version_tuple(version: str) -> tuple:
    parts = []
    for chunk in str(version or "").replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts or [0])


def add_yt_dlp_update_to_path(root: Path) -> None:
    wheel = yt_dlp_wheel_path(root)
    if wheel.exists() and str(wheel) not in sys.path:
        sys.path.insert(0, str(wheel))


def current_yt_dlp_version() -> str:
    try:
        from yt_dlp.version import __version__

        return str(__version__)
    except Exception:
        return "0"


def pypi_yt_dlp_payload(timeout: int = 12) -> dict:
    req = urllib.request.Request(
        "https://pypi.org/pypi/yt-dlp/json",
        headers={"User-Agent": "IMDLocal/yt-dlp-updater"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def select_wheel_url(payload: dict) -> str:
    urls = payload.get("urls") or []
    wheels = [item for item in urls if item.get("packagetype") == "bdist_wheel" and item.get("url")]
    if not wheels:
        return ""
    preferred = [
        item
        for item in wheels
        if "py3-none-any" in str(item.get("filename") or "").lower()
    ]
    return str((preferred or wheels)[0].get("url") or "")


def select_wheel_sha256(payload: dict, wheel_url: str) -> str:
    for item in payload.get("urls") or []:
        if str(item.get("url") or "") == wheel_url:
            return str((item.get("digests") or {}).get("sha256") or "").lower()
    return ""


def download_file(url: str, destination: Path, timeout: int = 60, expected_sha256: str = "") -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "IMDLocal/yt-dlp-updater"}, method="GET")
    digest = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                f.write(chunk)
    if expected_sha256 and digest.hexdigest().lower() != expected_sha256.lower():
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Hash SHA256 do update do yt-dlp nao confere.")
    tmp.replace(destination)


def check_yt_dlp_update(root: Path, force: bool = False) -> dict:
    meta_path = yt_dlp_meta_path(root)
    meta = load_json(meta_path)
    today = date.today().isoformat()
    if not force and meta.get("last_check") == today:
        return {"checked": False, "reason": "already_checked_today", **meta}

    current_version = current_yt_dlp_version()
    try:
        payload = pypi_yt_dlp_payload()
        latest_version = str((payload.get("info") or {}).get("version") or "")
        wheel_url = select_wheel_url(payload)
        wheel_sha256 = select_wheel_sha256(payload, wheel_url)
        if not latest_version or not wheel_url or not wheel_sha256:
            raise RuntimeError("PyPI nao retornou wheel e hash SHA256 do yt-dlp.")

        result = {
            "last_check": today,
            "current_version": current_version,
            "latest_version": latest_version,
            "updated": False,
        }
        if version_tuple(latest_version) > version_tuple(current_version):
            download_file(wheel_url, yt_dlp_wheel_path(root), expected_sha256=wheel_sha256)
            add_yt_dlp_update_to_path(root)
            result["updated"] = True
            result["current_version"] = latest_version
        save_json(meta_path, result)
        return {"checked": True, **result}
    except Exception as e:
        result = {
            "last_check": today,
            "current_version": current_version,
            "error": str(e),
            "updated": False,
        }
        save_json(meta_path, result)
        return {"checked": True, **result}


def print_banner() -> None:
    try:
        os.system(f"title {APP_NAME}")
    except Exception:
        pass
    print("=" * 64, flush=True)
    print(f" {APP_NAME}", flush=True)
    print("=" * 64, flush=True)
    print(" Painel local do IMD rodando nesta janela.", flush=True)
    print(" A pagina abre no navegador em alguns segundos.", flush=True)
    print(" Pode fechar esta janela depois que terminar de usar o app.", flush=True)
    print(" Se fechar agora, downloads e conversoes em andamento param.", flush=True)
    print("=" * 64, flush=True)


def prepare_runtime(root: Path) -> None:
    os.chdir(root)
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    add_yt_dlp_update_to_path(root)

    resources = resource_dir()
    ffmpeg_dir = resources / "vendor" / "ffmpeg"
    if ffmpeg_dir.exists():
        os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")

    config_file = root / "config.yaml"
    sample_file = resources / "config.sample.yaml"
    if not config_file.exists() and sample_file.exists():
        shutil.copy2(sample_file, config_file)


def open_browser_later(url: str) -> None:
    def _open() -> None:
        time.sleep(1.3)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def main() -> None:
    root = app_dir()
    prepare_runtime(root)

    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        import music_downloader

        music_downloader.main()
        return

    print_banner()
    update_result = check_yt_dlp_update(root)
    if update_result.get("updated"):
        print(f" yt-dlp atualizado para {update_result.get('latest_version')}.", flush=True)
    elif update_result.get("checked"):
        if update_result.get("error"):
            print(f" Nao foi possivel checar update do yt-dlp hoje: {update_result.get('error')}", flush=True)
        else:
            print(f" yt-dlp OK: {update_result.get('current_version')}.", flush=True)
    else:
        print(" Update diario do yt-dlp ja foi checado hoje.", flush=True)

    host = "127.0.0.1"
    port = "8765"
    if "--host" not in sys.argv:
        sys.argv.extend(["--host", host])
    if "--port" not in sys.argv:
        sys.argv.extend(["--port", port])

    open_browser_later(f"http://{host}:{port}")
    import app_server

    app_server.main()


if __name__ == "__main__":
    main()
