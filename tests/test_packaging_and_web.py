from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_preserves_existing_config_and_desktop_icon_is_default():
    source = (ROOT / "packaging" / "IMDInstaller.iss").read_text(encoding="utf-8")

    assert "if FileExists(ConfigPath) then begin" in source
    desktop_task = next(line for line in source.splitlines() if line.startswith('Name: "desktopicon"'))
    assert "unchecked" not in desktop_task


def test_web_rows_do_not_render_api_values_with_inner_html():
    source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "tr.innerHTML" not in source
    assert "item.innerHTML" not in source
    assert "appendSpotifyCell" in source


def test_docker_entrypoint_exists():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "main.py" not in dockerfile
    assert 'CMD ["python", "/app/music_downloader.py"]' in dockerfile


def test_pages_documents_smart_app_control_troubleshooting():
    source = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")

    assert 'id="problems"' in source
    assert "Problemas comuns na instalação" in source
    for asset in ("5-w.png", "6-w.png", "4-w.png", "3-w.png", "2-w.png", "1-w.png"):
        assert f'assets/{asset}' in source
        assert (ROOT / "docs" / "assets" / asset).is_file()
