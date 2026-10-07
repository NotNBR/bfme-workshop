@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\bfme_host\start.ps1 -Window -Battle orcs-elves %*
if errorlevel 1 pause
