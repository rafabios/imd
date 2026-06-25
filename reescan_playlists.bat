@echo off
cd /d C:\Users\rafa\Documents\apps\music_downloader_docker

echo ==============================
echo Using config.yaml
echo ==============================

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo.
echo ==============================
echo Running playlist reescan
echo ==============================

pip install --upgrade requests
pip install -U yt-dlp
python music_downloader.py --reescan-list

pause
