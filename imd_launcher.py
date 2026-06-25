import os
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(str(bundle_dir)).resolve()
    return app_dir()


def prepare_runtime(root: Path) -> None:
    os.chdir(root)
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

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
