@echo off
setlocal EnableExtensions
cls

rem Phase zero: immediately transfer execution to a temporary copy.
rem Running another batch file without CALL transfers control, so the repository
rem copy is never resumed after Git may replace it.
if /I "%~1"=="--drpm-temp" goto :DRPM_TEMP

set "DRPM_BOOT=%TEMP%\DavinciResolveProjectManagement-bootstrap-%RANDOM%-%RANDOM%.cmd"
copy /y "%~f0" "%DRPM_BOOT%" >nul || exit /b 1
"%DRPM_BOOT%" --drpm-temp "%~dp0"
set "DRPM_BOOT_RC=%ERRORLEVEL%"
del /q "%DRPM_BOOT%" >nul 2>nul
exit /b %DRPM_BOOT_RC%

:DRPM_TEMP
set "DRPM_REPO=%~2"
if not defined DRPM_REPO (
  echo ERROR: Repository path was lost during bootstrap.
  exit /b 1
)
if "%DRPM_REPO:~-1%"=="\" set "DRPM_REPO=%DRPM_REPO:~0,-1%"
set "DRPM_BRANCH=main"
set "DRPM_REMOTE=https://github.com/Suenee/DavinciResolveProjectManagement.git"
set "DRPM_RUNNER=%TEMP%\DavinciResolveProjectManagement-upgrade-%RANDOM%-%RANDOM%.ps1"

where git.exe >nul 2>nul
if errorlevel 1 (
  where winget.exe >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Git is missing and WinGet is unavailable.
    exit /b 1
  )
  echo Git is missing. Installing Git...
  winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements
  if errorlevel 1 exit /b %ERRORLEVEL%
  set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
  where git.exe >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Git installation completed but git.exe is not available.
    exit /b 1
  )
)

pushd "%DRPM_REPO%" >nul 2>nul
if errorlevel 1 (
  echo ERROR: Cannot access repository path: %DRPM_REPO%
  exit /b 1
)

set "GIT_CONFIG_COUNT=1"
set "GIT_CONFIG_KEY_0=safe.directory"
set "GIT_CONFIG_VALUE_0=%CD%"

if not exist ".git\" (
  echo Fresh bootstrap: initializing repository...
  for /f "delims=" %%F in ('dir /b /a 2^>nul') do (
    if /I not "%%F"=="upgrade.cmd" if /I not "%%F"=="logs" (
      echo ERROR: Fresh bootstrap directory is not empty: %%F
      popd
      exit /b 1
    )
  )
  git init
  if errorlevel 1 (popd & exit /b 1)
  git remote add origin "%DRPM_REMOTE%"
  if errorlevel 1 (popd & exit /b 1)
  git fetch origin %DRPM_BRANCH%
  if errorlevel 1 (popd & exit /b 1)
  git ls-files --error-unmatch upgrade.cmd >nul 2>nul
  if errorlevel 1 del /q "upgrade.cmd" >nul 2>nul
  git checkout -B %DRPM_BRANCH% origin/%DRPM_BRANCH%
  if errorlevel 1 (popd & exit /b 1)
) else (
  git remote get-url origin >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Existing Git repository has no origin remote.
    popd
    exit /b 1
  )
  git fetch origin %DRPM_BRANCH%
  if errorlevel 1 (popd & exit /b %ERRORLEVEL%)
)

git show origin/%DRPM_BRANCH%:upgrade.ps1 > "%DRPM_RUNNER%"
if errorlevel 1 (
  echo ERROR: Cannot obtain current upgrade.ps1 from origin/%DRPM_BRANCH%.
  popd
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DRPM_RUNNER%"
set "RC=%ERRORLEVEL%"
del /q "%DRPM_RUNNER%" >nul 2>nul
popd
exit /b %RC%
