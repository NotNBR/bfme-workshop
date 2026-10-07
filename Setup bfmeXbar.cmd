@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\bfme_host\setup.ps1 %*
if errorlevel 1 pause
