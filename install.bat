@echo off
rem Terrain Toolkit - manual installation (runs install.ps1)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
