@echo off
setlocal EnableExtensions
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

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python is not available in PATH.
    goto :error
)

if not exist "config.ini" (
    if not exist "config.example.ini" (
        echo ERROR: config.example.ini is missing.
        goto :error
    )
    copy /y "config.example.ini" "config.ini" >nul
    echo Created config.ini from config.example.ini.
) else (
    echo Keeping existing config.ini.
)

set "DVR_MODULE=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
if exist "%DVR_MODULE%" (
    echo DaVinci Resolve scripting module found.
) else (
    echo WARNING: DaVinci Resolve scripting module was not found at:
    echo   %DVR_MODULE%
    echo Install DaVinci Resolve Studio 21 and verify the scripting components.
)

python -m py_compile "resolve_project_builder.py"
if errorlevel 1 goto :error

echo.
echo Upgrade completed successfully.
exit /b 0

:error
echo.
echo Upgrade failed.
pause
exit /b 1
