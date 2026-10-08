@echo off
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\launch.ps1 --window --battle orcs-elves %*
if errorlevel 1 pause
