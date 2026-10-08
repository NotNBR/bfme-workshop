@echo off
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\launch.ps1 --eight-kingdoms %*
if errorlevel 1 pause
