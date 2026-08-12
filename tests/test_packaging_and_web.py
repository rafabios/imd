from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_preserves_existing_config_and_desktop_icon_is_default():
    source = (ROOT / "packaging" / "IMDInstaller.iss").read_text(encoding="utf-8")

    assert "if FileExists(ConfigPath) then begin" in source
    assert 'Excludes: "config.yaml,spotify_secrets.yaml,runtime_updates\\*,config_backups\\*,imports\\*,tasks\\*"' in source
    desktop_task = next(line for line in source.splitlines() if line.startswith('Name: "desktopicon"'))
    assert "unchecked" not in desktop_task


def test_packaged_ui_smoke_uses_disposable_copy_and_checks_bundle_cleanliness():
    source = (ROOT / ".github" / "workflows" / "build-msi.yml").read_text(encoding="utf-8")

    assert 'Copy-Item -Path "dist\\IMD" -Destination $smokeDir -Recurse -Force' in source
    assert "Start-Process -FilePath $smokeExe" in source
    assert "Remove-Item -LiteralPath $smokeDir -Recurse -Force" in source
    assert '"dist\\IMD\\config.yaml"' in source
    assert '"dist\\IMD\\runtime_updates"' in source


def test_web_rows_do_not_render_api_values_with_inner_html():
    source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert "tr.innerHTML" not in source
    assert "item.innerHTML" not in source
    assert "appendSpotifyCell" in source


def test_web_exposes_tagging_shortcut_and_flexible_row_selection():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert html.count("data-tag-music") == 2
    assert 'id="sheet-row-selection"' in html
    assert 'id="select-all-sheet"' in html
    assert 'id="select-visible-sheet"' in html
    assert 'id="download-only-row" type="text"' in html
    assert "/api/tag-music/start" in script
    assert "parseSheetRowSelection" in script
    assert "row_selection: downloadOnlyRowEl.value.trim()" in script
    assert ".tag-action" in styles


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


def test_pages_loads_latest_release_version_safely():
    source = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")

    assert 'data-latest-version' in source
    assert '<script src="site.js" defer></script>' in source
    assert "repos/rafabios/imd/releases/latest" in script
    assert "node.textContent = tag" in script
    assert "innerHTML" not in script


def test_macos_workflow_builds_both_architectures_without_developer_certificate():
    workflow = (ROOT / ".github" / "workflows" / "build-macos.yml").read_text(encoding="utf-8")
    spec = (ROOT / "packaging" / "IMD-macos.spec").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-macos.txt").read_text(encoding="utf-8")

    assert "macos-15-intel" in workflow
    assert "macos-15" in workflow
    assert "Apple-Silicon" in workflow
    assert "hdiutil create" in workflow
    assert "hdiutil verify" in workflow
    assert "codesign --verify --deep --strict" in workflow
    assert '"$bundled_ffmpeg" -version' in workflow
    assert "notarytool" not in workflow
    assert "APPLE_CERTIFICATE" not in workflow
    assert "BUNDLE(" in spec
    assert 'codesign_identity=None' in spec
    assert "--only-binary=numba,llvmlite -r requirements-macos.txt" in workflow
    assert "python -m pip check" in workflow
    assert "numba==0.60.0" in requirements
    assert "llvmlite==0.43.0" in requirements


def test_pages_offer_macos_downloads():
    source = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")

    assert "latest-macOS-Apple-Silicon.dmg" in source
    assert "latest-macOS-Intel.dmg" in source
    assert 'id="install-macos"' in source


def test_macos_dmg_includes_unlock_instructions():
    instructions = (ROOT / "packaging" / "macos" / "LEIA-ME-macOS.txt").read_text(encoding="utf-8")

    assert "Abrir Mesmo Assim" in instructions
    assert "xattr -dr com.apple.quarantine" in instructions
    assert "desativar o Gatekeeper globalmente" in instructions
