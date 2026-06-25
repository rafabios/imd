@echo off
cd /d C:\Users\rafa\Documents\apps\music_downloader_docker

chcp 65001 >nul
set PYTHONUTF8=1

echo ==============================
echo Starting IMD Insane Music Downloader
echo ==============================
echo.
echo Open: http://127.0.0.1:8765
echo Keep this window open while using the panel.
echo.

start "" /min cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8765"
python app_server.py --host 127.0.0.1 --port 8765

pause
