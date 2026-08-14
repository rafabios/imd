from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_setup_preserves_existing_config_and_desktop_icon_is_default():
    source = (ROOT / "packaging" / "IMDInstaller.iss").read_text(encoding="utf-8")

    assert "if FileExists(ConfigPath) then begin" in source
    assert 'Excludes: "config.yaml,spotify_secrets.yaml,runtime_updates\\*,config_backups\\*,imports\\*,tasks\\*"' in source
    desktop_task = next(line for line in source.splitlines() if line.startswith('Name: "desktopicon"'))
    assert "unchecked" not in desktop_task


def test_setup_only_asks_for_music_and_uses_internal_state_folder():
    source = (ROOT / "packaging" / "IMDInstaller.iss").read_text(encoding="utf-8")

    assert "SheetPage" not in source
    assert "StateDirPage" not in source
    assert "CreateInputQueryPage" not in source
    assert "URL CSV da planilha" not in source
    assert "DefaultMusicFolder" in source
    assert "User Shell Folders" in source
    assert "'My Music'" in source
    assert "{localappdata}\\IMD Insane Music Downloader\\state" in source
    assert "LoadStringsFromFile" in source
    assert "SaveStringsToUTF8FileWithoutBOM" in source
    assert 'Source: "..\\config.sample.yaml"; DestDir: "{tmp}"; DestName: "imd-config.sample.yaml"' in source
    assert "{tmp}\\imd-config.sample.yaml" in source
    assert "{app}\\_internal\\config.sample.yaml" in source


def test_setup_smoke_checks_known_music_folder_hidden_state_and_blank_sheet():
    source = (ROOT / ".github" / "workflows" / "build-msi.yml").read_text(encoding="utf-8")

    assert "[Environment+SpecialFolder]::MyMusic" in source
    assert 'Join-Path $installDir "state"' in source
    assert 'google_sheet_csv:\\s*""' in source
    assert "candidate_limit:\\s*6" in source
    assert '"/LOG=$setupInstallLog"' in source
    assert "dist/setup-install.log" in source


def test_windows_workflow_accepts_inno_setup_6_or_7():
    source = (ROOT / ".github" / "workflows" / "build-msi.yml").read_text(encoding="utf-8")

    assert "Inno Setup 7\\ISCC.exe" in source
    assert "Inno Setup 6\\ISCC.exe" in source


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


def test_web_configuration_creates_google_sheet_and_hides_internal_state():
    script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'createLink.href = "https://sheets.new"' in script
    assert '"paths.state_dir"' in script
    assert "hiddenConfigFields.has(path)" in script
    assert "JSON.parse(JSON.stringify(currentConfig))" in script
    assert "Qualquer pessoa com o link" in script


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


def test_web_exposes_music_analysis_library_scan_and_drag_drop():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert html.count("data-open-analysis") == 2
    assert 'id="analysis"' in html
    assert 'id="start-library-analysis"' in html
    assert 'id="analysis-drop-zone"' in html
    assert 'id="analysis-file"' in html
    assert 'id="analysis-chart"' in html
    assert "/api/analysis/start-library" in script
    assert "/api/analysis/upload" in script
    assert 'addEventListener("drop"' in script
    assert "drawAnalysisChart" in script
    assert ".analysis-action" in styles
    assert ".quality-badge.good" in styles


def test_workflows_compile_audio_analysis_module():
    windows = (ROOT / ".github" / "workflows" / "build-msi.yml").read_text(encoding="utf-8")
    macos = (ROOT / ".github" / "workflows" / "build-macos.yml").read_text(encoding="utf-8")

    assert "py_compile app_server.py music_downloader.py imd_launcher.py imd_paths.py google_sheets.py audio_analysis.py" in windows
    assert "py_compile app_server.py music_downloader.py imd_launcher.py imd_paths.py google_sheets.py audio_analysis.py" in macos


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
