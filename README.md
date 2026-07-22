# IMD Insane Music Downloader

Aplicativo local para importar listas de musicas, indexar playlists e artistas publicos do Spotify, localizar as faixas no YouTube com `yt-dlp`, converter o audio com FFmpeg e manter historico idempotente.

## Instalacao no Windows

O projeto gera dois instaladores:

- `IMD-Insane-Music-Downloader-*-Setup.exe`: recomendado. Permite escolher as pastas e a planilha durante a instalacao.
- `IMD-Insane-Music-Downloader-*.msi`: instalador tecnico para automacao.

Os instaladores sao gerados em `Actions > Build Windows Installers`. Para publicar uma versao:

```bash
git tag v0.1.7
git push origin v0.1.7
```

Tags `v*` geram uma GitHub Release com Setup, MSI e `SHA256SUMS.txt`.

Atualizacoes pelo Setup preservam o `config.yaml` existente. O aplicativo e instalado por usuario em `AppData`, cria atalhos e inclui FFmpeg.

## Execucao pelo codigo-fonte

Recomendado: Python 3.12.

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy config.sample.yaml config.yaml
.venv\Scripts\python imd_launcher.py
```

Edite `config.yaml` antes da primeira execucao. Os campos principais sao:

- `source.google_sheet_csv`: URL CSV do Google Sheets;
- `paths.music_dir`: pasta onde as musicas serao salvas;
- `paths.state_dir`: pasta de historico, erros e cache;
- `audio.format` e `audio.quality`: formato e qualidade;
- `spotify.mode`: processamento de links publicos do Spotify.

O painel abre em `http://127.0.0.1:8765`.

## Testes

```bash
python -m pytest -q
python -m py_compile app_server.py music_downloader.py imd_launcher.py
```

## Docker

Prepare um `config.docker.yaml` a partir de `config.sample.yaml`, usando caminhos do contêiner:

```yaml
paths:
  music_dir: "/music"
  state_dir: "/state"
```

Depois execute:

```bash
docker build -t imd:latest .
docker run --rm -it \
  -v "$(pwd)/config.docker.yaml:/app/config.yaml:ro" \
  -v "$(pwd)/music:/music" \
  -v "$(pwd)/state:/state" \
  imd:latest
```

O contêiner inclui FFmpeg, certificados CA e Deno.

## Estrutura

- `music_downloader.py`: downloads, Spotify, conversao, tags e historico;
- `app_server.py`: API e painel local;
- `imd_launcher.py`: inicializacao e atualizacao do `yt-dlp`;
- `web/`: interface do painel;
- `packaging/`: instaladores Windows;
- `tests/`: testes automatizados.
