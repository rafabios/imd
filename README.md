# IMD Insane Music Downloader

## Windows installer

Este projeto inclui um GitHub Actions workflow para gerar instaladores Windows do painel local.

- `IMD-Insane-Music-Downloader-*-Setup.exe`: recomendado para usuario final. Abre um assistente com Next/Avancar para escolher pasta de musicas, pasta de estado e URL CSV da planilha do Google.
- `IMD-Insane-Music-Downloader-*.msi`: instalador tecnico/silencioso, util para automacao.

Como gerar:

- Suba o projeto no GitHub.
- Abra `Actions` > `Build Windows Installers` > `Run workflow`.
- Baixe o artefato `IMD-Insane-Music-Downloader-Windows-Installers`.

Para publicar uma versao:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Quando a tag `v*` for enviada, o workflow gera o `.exe`, o `.msi` e anexa os arquivos no GitHub Release.

Os instaladores sao por usuario, instalam em `AppData`, criam atalho no Menu Iniciar e incluem o `ffmpeg` baixado durante o build. Se o Windows bloquear o setup baixado do GitHub, clique com o botao direito no arquivo, abra `Propriedades`, marque `Desbloquear` e execute de novo. O arquivo `SHA256SUMS.txt` publicado junto ajuda a conferir o download.

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
