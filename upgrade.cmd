@echo off
setlocal EnableExtensions
cls
cd /d "%~dp0"
set "DRPM_REPO=%CD%"
set "DRPM_BRANCH=main"
set "DRPM_RUNNER=%TEMP%\DavinciResolveProjectManagement-upgrade-%RANDOM%-%RANDOM%.ps1"

where git.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git was not found.
  exit /b 1
)

git fetch origin %DRPM_BRANCH%
if errorlevel 1 exit /b %ERRORLEVEL%

git show origin/%DRPM_BRANCH%:upgrade.ps1 > "%DRPM_RUNNER%"
if errorlevel 1 (
  echo ERROR: Cannot obtain current upgrade.ps1 from origin/%DRPM_BRANCH%.
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DRPM_RUNNER%"
set "RC=%ERRORLEVEL%"
del /q "%DRPM_RUNNER%" >nul 2>nul
exit /b %RC%
