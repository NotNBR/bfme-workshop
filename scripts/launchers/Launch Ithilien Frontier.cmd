@echo off
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\launch.ps1 --frontier %*
if errorlevel 1 pause
