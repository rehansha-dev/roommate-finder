@echo off
cd /d "%~dp0"
echo Starting Roommate Finder at http://127.0.0.1:10000
echo Keep this window open while using the website.
.venv\Scripts\python.exe app.py
pause
