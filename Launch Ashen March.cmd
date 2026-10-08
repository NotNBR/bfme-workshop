@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe tools\bfme_host\launch.py --ashen
pause
