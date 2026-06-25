# IMD Insane Music Downloader

## Windows installer

Este projeto inclui um GitHub Actions workflow para gerar um instalador `.msi` do painel local.

Como gerar:

- Suba o projeto no GitHub.
- Abra `Actions` > `Build Windows MSI` > `Run workflow`.
- Baixe o artefato `IMD-Insane-Music-Downloader-MSI`.

Para publicar uma versao:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Quando a tag `v*` for enviada, o workflow gera o `.msi` e anexa o arquivo no GitHub Release.

O instalador e por usuario, instala em `AppData`, cria atalho no Menu Iniciar e inclui o `ffmpeg` baixado durante o build.

This container runs a Python script that:
- Reads a Google Sheets CSV export (or your override URL)
- Downloads individual tracks from YouTube (yt-dlp)
- Optionally downloads Spotify playlists using spotdl
- Converts audio to MP3 (320kbps by default)
- Optionally detects BPM (fast method)
- Writes logs to `data/erros.txt` and keeps an idempotent history in `data/historico.txt`

## 1) Files in this template
- `Dockerfile`
- `requirements.txt`
- `.env` (template)
- `main.py` (script)

## 2) Configure
Edit `.env`:

- Optional (recommended):
  - `SPOTIPY_CLIENT_ID`
  - `SPOTIPY_CLIENT_SECRET`

- Optional:
  - `GOOGLE_SHEET_CSV`
  - `DETECT_BPM=1` (set 0 to disable)
  - `QUALITY_AUDIO=320`

## 3) Build

```bash
docker build -t music-downloader:latest .
```

## 4) Run

Mount two folders so downloads/logs persist:

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/data:/app/data" \
  music-downloader:latest
```

## Notes
- This image installs **deno** to avoid yt-dlp warnings about missing JavaScript runtime.
- If you hit Spotify rate limits, add your Spotify credentials (above).
