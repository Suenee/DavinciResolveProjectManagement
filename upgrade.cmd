@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo === DaVinci Resolve Project Management upgrade ===

if exist ".git\" (
    where git >nul 2>nul
    if errorlevel 1 (
        echo WARNING: Git repository found, but git.exe is not available. Skipping git pull.
    ) else (
        echo Updating repository...
        git pull --ff-only
        if errorlevel 1 goto :error
    )
)

call :find_python
if not defined PYTHON_EXE (
    echo Python was not found. Installing Python 3.13...
    call :install_python
    if errorlevel 1 goto :error
    call :find_python
)
if not defined PYTHON_EXE (echo ERROR: Python installation finished, but python.exe could not be located.& goto :error)

echo Python found: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if errorlevel 1 goto :error

if not exist "config.ini" (
    if not exist "config.example.ini" (echo ERROR: config.example.ini is missing.& goto :error)
    copy /y "config.example.ini" "config.ini" >nul
    echo Created config.ini from config.example.ini.
) else (
    echo Keeping existing config.ini.
)

set "DVR_MODULE=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
if exist "%DVR_MODULE%" (echo DaVinci Resolve scripting module found.) else (
    echo WARNING: DaVinci Resolve scripting module was not found at:
    echo   %DVR_MODULE%
)

echo Checking Python sources...
"%PYTHON_EXE%" -m py_compile "resolve_project_builder.py" "managed_builder" "resolve_lifecycle" "resolve_gui.py"
if errorlevel 1 goto :error

if not exist "runtime" mkdir "runtime" >nul 2>nul

echo.
echo Upgrade completed successfully.
exit /b 0

:find_python
set "PYTHON_EXE="
for %%P in (python.exe python3.exe) do (
    where %%P >nul 2>nul
    if not errorlevel 1 for /f "delims=" %%I in ('where %%P 2^>nul') do if not defined PYTHON_EXE (
        "%%I" --version >nul 2>nul
        if not errorlevel 1 set "PYTHON_EXE=%%I"
    )
)
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_EXE if exist "%ProgramFiles%\Python313\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python313\python.exe"
if not defined PYTHON_EXE if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python314\python.exe"
exit /b 0

:install_python
where winget >nul 2>nul
if not errorlevel 1 (
    echo Trying installation through winget...
    winget install --id Python.Python.3.13 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 (call :find_python& if defined PYTHON_EXE exit /b 0)
)
set "PYTHON_VERSION=3.13.14"
set "PYTHON_ARCH=amd64"
if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "PYTHON_ARCH=arm64"
if /I "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "PYTHON_ARCH=arm64"
set "PYTHON_INSTALLER=%TEMP%\python-%PYTHON_VERSION%-%PYTHON_ARCH%.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-%PYTHON_ARCH%.exe"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 exit /b 1
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1 Include_test=0 Shortcuts=0
set "INSTALL_RC=%ERRORLEVEL%"
del /q "%PYTHON_INSTALLER%" >nul 2>nul
if not "%INSTALL_RC%"=="0" exit /b %INSTALL_RC%
call :find_python
if not defined PYTHON_EXE exit /b 1
exit /b 0

:error
echo.
echo Upgrade failed.
pause
exit /b 1
