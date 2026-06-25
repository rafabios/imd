import json
import shutil
import sys
import threading
import uuid
import urllib.request
from http.server import ThreadingHTTPServer

import app_server


def setup_function():
    app_server.TASKS.clear()
    app_server.IMPORTS.clear()


def test_flatten_config_paths():
    data = {"audio": {"format": "mp3"}, "conversion": {"workers": 4}}

    assert app_server.flatten_config_paths(data) == ["audio.format", "conversion.workers"]


def test_dashboard_data_loads_current_config():
    data = app_server.load_dashboard_data()

    assert data["ok"] is True
    assert "config" in data
    assert "summary" in data
    assert data["validation"]["ok"] is True
    assert data["summary"]["conversion_workers"] == data["config"]["conversion"]["workers"]


def test_save_config_creates_backup(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    sample_path = tmp_path / "config.sample.yaml"
    backup_dir = tmp_path / "backups"
    shutil.copy2(app_server.CONFIG_FILE, config_path)
    shutil.copy2(app_server.SAMPLE_CONFIG_FILE, sample_path)

    monkeypatch.setattr(app_server, "CONFIG_FILE", config_path)
    monkeypatch.setattr(app_server, "SAMPLE_CONFIG_FILE", sample_path)
    monkeypatch.setattr(app_server, "BACKUP_DIR", backup_dir)

    config = app_server.read_yaml_file(config_path)
    config["conversion"]["workers"] = 2
    result = app_server.save_config(config)
    saved = app_server.read_yaml_file(config_path)

    assert result["ok"] is True
    assert saved["conversion"]["workers"] == 2
    assert len(list(backup_dir.glob("config_*.yaml"))) == 1


def test_save_config_rejects_missing_fields(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    sample_path = tmp_path / "config.sample.yaml"
    shutil.copy2(app_server.CONFIG_FILE, config_path)
    shutil.copy2(app_server.SAMPLE_CONFIG_FILE, sample_path)

    monkeypatch.setattr(app_server, "CONFIG_FILE", config_path)
    monkeypatch.setattr(app_server, "SAMPLE_CONFIG_FILE", sample_path)
    monkeypatch.setattr(app_server, "BACKUP_DIR", tmp_path / "backups")

    config = app_server.read_yaml_file(config_path)
    del config["conversion"]["workers"]
    result = app_server.save_config(config)

    assert result["ok"] is False
    assert "conversion.workers" in result["validation"]["messages"][0]


def test_background_task_captures_logs():
    task = app_server.start_background_task(
        "test",
        [sys.executable, "-c", "print('hello from task')"],
    )

    for _ in range(50):
        snapshot = app_server.task_payload(task.id)["task"]
        if snapshot["status"] in ("succeeded", "failed"):
            break
        threading.Event().wait(0.1)

    payload = app_server.task_payload(task.id)
    assert payload["ok"] is True
    assert payload["task"]["status"] == "succeeded"
    assert "hello from task" in "\n".join(payload["task"]["logs"])


def test_worker_command_switches_when_packaged(monkeypatch):
    monkeypatch.setattr(app_server.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_server.sys, "executable", r"C:\IMD\IMD.exe")

    command = app_server.worker_command("--conversion-only")

    assert command == [r"C:\IMD\IMD.exe", "--worker", "--conversion-only"]


def test_resource_root_uses_pyinstaller_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(app_server.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert app_server.resource_root_dir() == tmp_path.resolve()


def test_start_conversion_task_reuses_running_task(monkeypatch):
    task = app_server.BackgroundTask(
        id="running-task",
        kind="conversion",
        command=["python"],
        status="running",
        started_at="2099-01-01T00:00:00",
    )
    monkeypatch.setitem(app_server.TASKS, task.id, task)

    result = app_server.start_conversion_task()

    assert result["ok"] is False
    assert result["task"]["id"] == "running-task"


def test_start_download_task_builds_expected_command(monkeypatch):
    captured = {}

    def fake_start_background_task(kind, command):
        captured["kind"] = kind
        captured["command"] = command
        return app_server.BackgroundTask(id="download-task", kind=kind, command=command)

    monkeypatch.setattr(app_server, "start_background_task", fake_start_background_task)

    result = app_server.start_download_task(
        {
            "reescan_list": True,
            "dry_run": True,
            "only_row": "7",
            "only_url": "https://open.spotify.com/playlist/abc",
            "tagmusic": False,
        }
    )

    assert result["ok"] is True
    assert captured["kind"] == "download"
    assert "--reescan-list" in captured["command"]
    assert "--dry-run" in captured["command"]
    assert captured["command"][captured["command"].index("--only-row") + 1] == "7"
    assert captured["command"][captured["command"].index("--only-url") + 1] == "https://open.spotify.com/playlist/abc"
    assert "--no-tagmusic" in captured["command"]


def test_start_download_task_rejects_parallel_download(monkeypatch):
    task = app_server.BackgroundTask(
        id="running-download",
        kind="download",
        command=["python"],
        status="running",
        started_at="2099-01-01T00:00:00",
    )
    monkeypatch.setitem(app_server.TASKS, task.id, task)

    result = app_server.start_download_task({"dry_run": True})

    assert result["ok"] is False
    assert result["task"]["id"] == "running-download"


def test_start_import_download_task_builds_input_file_command(monkeypatch, tmp_path):
    imported_csv = tmp_path / "import.csv"
    imported_csv.write_text("Artista,Musica,(opcional) Tag/Genero,Spotify Playlist (link)\nA,T,G,\n", encoding="utf-8")
    app_server.IMPORTS["abc"] = {"csv_path": str(imported_csv), "filename": "tracks.csv"}
    captured = {}

    def fake_start_background_task(kind, command):
        captured["kind"] = kind
        captured["command"] = command
        return app_server.BackgroundTask(id="import-download", kind=kind, command=command)

    monkeypatch.setattr(app_server, "start_background_task", fake_start_background_task)

    result = app_server.start_import_download_task("abc", {"dry_run": True, "reescan_list": False})

    assert result["ok"] is True
    assert captured["kind"] == "download"
    assert captured["command"][captured["command"].index("--input-file") + 1] == str(imported_csv)
    assert "--dry-run" in captured["command"]
    assert "--no-reescan-list" in captured["command"]


def test_start_rows_download_task_builds_import_file(monkeypatch, tmp_path):
    monkeypatch.setattr(app_server, "IMPORT_DIR", tmp_path)
    captured = {}

    def fake_start_background_task(kind, command):
        captured["kind"] = kind
        captured["command"] = command
        return app_server.BackgroundTask(id="rows-download", kind=kind, command=command)

    monkeypatch.setattr(app_server, "start_background_task", fake_start_background_task)

    result = app_server.start_rows_download_task(
        [{"Artista": "A", "Musica": "T", "(opcional) Tag/Genero": "G"}],
        {"dry_run": True, "reescan_list": True},
    )

    assert result["ok"] is True
    csv_path = captured["command"][captured["command"].index("--input-file") + 1]
    assert app_server.Path(csv_path).exists()
    assert "--dry-run" in captured["command"]
    assert "--reescan-list" in captured["command"]


def test_task_persistence_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(app_server, "TASK_DIR", tmp_path)
    task = app_server.BackgroundTask(id="persisted", kind="download", command=["python"], status="succeeded")
    task.logs.append("Resumo: linhas=2 | playlists=0 | artistas=0 | manuais=2 | novas=1 | existentes=0 | historico=0 | dry_run=0 | falhas=1 | ignoradas=0")
    app_server.update_task_progress_from_line(task, task.logs[-1])
    app_server.persist_task(task)
    app_server.TASKS.clear()
    app_server.load_persisted_tasks()

    loaded = app_server.TASKS["persisted"]
    assert loaded.status == "succeeded"
    assert loaded.progress["rows"] == 2
    assert loaded.progress["failed"] == 1


def test_validate_rows_reports_issues():
    result = app_server.validate_rows(
        [
            {"Artista": "A", "Musica": "T", "(opcional) Tag/Genero": ""},
            {"Artista": "A", "Musica": "T", "(opcional) Tag/Genero": ""},
            {"Spotify Playlist (link)": "not spotify"},
            {},
        ]
    )

    assert result["ok"] is True
    assert result["counts"]["issues"] >= 4


def test_history_payload_reads_state_files(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    sample_path = tmp_path / "config.sample.yaml"
    shutil.copy2(app_server.CONFIG_FILE, config_path)
    shutil.copy2(app_server.SAMPLE_CONFIG_FILE, sample_path)
    config = app_server.read_yaml_file(config_path)
    config["paths"]["state_dir"] = str(tmp_path)
    app_server.write_yaml_file(config_path, config)
    (tmp_path / "erros.txt").write_text("erro 1\n", encoding="utf-8")
    (tmp_path / "baixados.txt").write_text("ok 1\n", encoding="utf-8")
    (tmp_path / "failed_items.jsonl").write_text('{"artist":"A","title":"T","genre":"G","error":"x"}\n', encoding="utf-8")
    monkeypatch.setattr(app_server, "CONFIG_FILE", config_path)
    monkeypatch.setattr(app_server, "SAMPLE_CONFIG_FILE", sample_path)

    payload = app_server.load_history_payload()

    assert payload["ok"] is True
    assert payload["files"]["erros"] == ["erro 1"]
    assert payload["files"]["baixados"] == ["ok 1"]
    assert payload["files"]["failed_items"]


def test_failure_lines_to_rows_extracts_download_queries():
    rows = app_server.failure_lines_to_rows(
        [
            "[2026-01-01] [YOUTUBE] File not found after download: Artist - Track :: error",
            "[2026-01-01] [YOUTUBE] Exception: Loose Query :: error",
        ]
    )

    assert rows == [{"Artista": "Artist", "Musica": "Track"}, {"Musica": "Loose Query"}]


def test_start_failure_retry_task(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    sample_path = tmp_path / "config.sample.yaml"
    shutil.copy2(app_server.CONFIG_FILE, config_path)
    shutil.copy2(app_server.SAMPLE_CONFIG_FILE, sample_path)
    config = app_server.read_yaml_file(config_path)
    config["paths"]["state_dir"] = str(tmp_path)
    app_server.write_yaml_file(config_path, config)
    (tmp_path / "failed_items.jsonl").write_text('{"artist":"A","title":"T","genre":"G","error":"boom"}\n', encoding="utf-8")
    monkeypatch.setattr(app_server, "CONFIG_FILE", config_path)
    monkeypatch.setattr(app_server, "SAMPLE_CONFIG_FILE", sample_path)
    monkeypatch.setattr(app_server, "IMPORT_DIR", tmp_path / "imports")
    captured = {}

    def fake_start_background_task(kind, command):
        captured["command"] = command
        return app_server.BackgroundTask(id="retry", kind=kind, command=command)

    monkeypatch.setattr(app_server, "start_background_task", fake_start_background_task)

    result = app_server.start_failure_retry_task({"dry_run": True})

    assert result["ok"] is True
    assert "--input-file" in captured["command"]


def test_environment_payload_contains_checks():
    payload = app_server.environment_payload()

    assert payload["ok"] is True
    assert any(check["name"] == "Python" for check in payload["checks"])


def test_http_health_endpoint():
    server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/health"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    assert payload == {"ok": True, "app": "imd-insane-music-downloader"}


def test_http_config_post(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    sample_path = tmp_path / "config.sample.yaml"
    backup_dir = tmp_path / "backups"
    shutil.copy2(app_server.CONFIG_FILE, config_path)
    shutil.copy2(app_server.SAMPLE_CONFIG_FILE, sample_path)

    monkeypatch.setattr(app_server, "CONFIG_FILE", config_path)
    monkeypatch.setattr(app_server, "SAMPLE_CONFIG_FILE", sample_path)
    monkeypatch.setattr(app_server, "BACKUP_DIR", backup_dir)

    config = app_server.read_yaml_file(config_path)
    config["conversion"]["workers"] = 3

    server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/config"
        body = json.dumps({"config": config}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    assert payload["ok"] is True
    assert payload["config"]["conversion"]["workers"] == 3


def test_sheet_preview_from_configured_csv(monkeypatch, tmp_path):
    csv_path = tmp_path / "sheet.csv"
    csv_path.write_text(
        "Artista,Musica,(opcional) Tag/Genero,Spotify Playlist (link)\n"
        "Artist One,Track One,Prog,\n"
        ",,Fullon,https://open.spotify.com/playlist/abc\n"
        ",,Dark,https://open.spotify.com/artist/def\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "config.yaml"
    sample_path = tmp_path / "config.sample.yaml"
    shutil.copy2(app_server.CONFIG_FILE, config_path)
    shutil.copy2(app_server.SAMPLE_CONFIG_FILE, sample_path)

    config = app_server.read_yaml_file(config_path)
    config["source"]["google_sheet_csv"] = str(csv_path)
    app_server.write_yaml_file(config_path, config)

    monkeypatch.setattr(app_server, "CONFIG_FILE", config_path)
    monkeypatch.setattr(app_server, "SAMPLE_CONFIG_FILE", sample_path)

    preview = app_server.load_sheet_preview()

    assert preview["ok"] is True
    assert preview["counts"]["total"] == 3
    assert preview["counts"]["manual"] == 1
    assert preview["counts"]["playlist"] == 1
    assert preview["counts"]["artist"] == 1
    assert preview["rows"][0]["artist"] == "Artist One"


def test_read_sheet_dataframe_uses_requests_for_http(monkeypatch):
    class FakeResponse:
        content = b"Artista,Musica\nA,T\n"
        encoding = "utf-8"

        def raise_for_status(self):
            return None

    calls = []

    def fake_get(url, timeout, verify, headers):
        calls.append((url, timeout, verify, headers["User-Agent"]))
        return FakeResponse()

    monkeypatch.setattr(app_server.requests, "get", fake_get)

    df = app_server.read_sheet_dataframe("https://example.test/sheet.csv", disable_ssl_verify=True)

    assert calls == [("https://example.test/sheet.csv", 30, False, "IMDLocal/0.1")]
    assert df.iloc[0]["Artista"] == "A"


def test_parse_txt_import(monkeypatch, tmp_path):
    monkeypatch.setattr(app_server, "IMPORT_DIR", tmp_path)
    result = app_server.parse_import_file(
        "tracks.txt",
        b"Artist One - Track One\nhttps://open.spotify.com/playlist/abc\nLoose Title\n",
    )

    assert result["ok"] is True
    assert result["counts"]["total"] == 3
    assert result["counts"]["manual"] == 2
    assert result["counts"]["playlist"] == 1
    assert result["rows"][0]["artist"] == "Artist One"
    assert result["rows"][0]["title"] == "Track One"
    assert app_server.Path(result["csv_path"]).exists()


def test_parse_csv_import(monkeypatch, tmp_path):
    monkeypatch.setattr(app_server, "IMPORT_DIR", tmp_path)
    result = app_server.parse_import_file(
        "tracks.csv",
        "Artista,Musica,Genero\nA,T,G\n".encode("utf-8"),
    )

    assert result["ok"] is True
    assert result["rows"][0]["artist"] == "A"
    assert result["rows"][0]["title"] == "T"
    assert result["rows"][0]["genre"] == "G"
    assert app_server.Path(result["csv_path"]).exists()


def test_http_task_status_endpoint():
    task = app_server.start_background_task(
        "http-test",
        [sys.executable, "-c", "print('status endpoint')"],
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/tasks/{task.id}"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    assert payload["ok"] is True
    assert payload["task"]["id"] == task.id


def test_http_tasks_endpoint():
    app_server.TASKS["abc"] = app_server.BackgroundTask(id="abc", kind="download", command=["python"], status="succeeded")
    server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/tasks"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    assert payload["ok"] is True
    assert payload["tasks"][0]["id"] == "abc"


def test_http_import_preview_endpoint():
    boundary = "----pytest-" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="tracks.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "A - T\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    server = ThreadingHTTPServer(("127.0.0.1", 0), app_server.AppHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/import/preview"
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    assert payload["ok"] is True
    assert payload["rows"][0]["artist"] == "A"
    assert payload["rows"][0]["title"] == "T"
