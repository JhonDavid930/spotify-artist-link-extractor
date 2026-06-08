@echo off
cd /d "%~dp0"
if exist "dist\SpotifyLicenseStudio.exe" (
    start "" "dist\SpotifyLicenseStudio.exe"
) else (
    start "" ".venv\Scripts\pythonw.exe" "tools\license_studio.py"
)
