@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
echo === DaVinci Resolve Project Management upgrade ===
if exist ".git\" (
 where git >nul 2>nul
 if not errorlevel 1 (echo Updating repository...& git pull --ff-only& if errorlevel 1 goto :error)
)
call :find_python
if not defined PYTHON_EXE (echo Python was not found. Installing Python 3.13...& call :install_python& if errorlevel 1 goto :error& call :find_python)
if not defined PYTHON_EXE (echo ERROR: Python could not be located.& goto :error)
echo Python found: %PYTHON_EXE%
"%PYTHON_EXE%" --version
if errorlevel 1 goto :error
if not exist "config.example.ini" (echo ERROR: config.example.ini is missing.& goto :error)
echo Migrating configuration...
"%PYTHON_EXE%" "%~dp0config_migrate.py"
if errorlevel 1 goto :error
set "DVR_MODULE=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
if exist "%DVR_MODULE%" (echo DaVinci Resolve scripting module found.) else (echo WARNING: DaVinci Resolve scripting module was not found at:& echo   %DVR_MODULE%)
echo Checking Python sources...
"%PYTHON_EXE%" -m py_compile "resolve_project_builder.py" "managed_builder.py" "managed_builder_runner.py" "timeline_audio.py" "resolve_lifecycle.py" "resolve_gui.py" "config_migrate.py"
if errorlevel 1 goto :error
if not exist "runtime" mkdir "runtime" >nul 2>nul
if not exist "runtime\logs" mkdir "runtime\logs" >nul 2>nul
echo.
echo Upgrade completed successfully.
exit /b 0
:find_python
set "PYTHON_EXE="
for %%P in (python.exe python3.exe) do for /f "delims=" %%I in ('where %%P 2^>nul') do if not defined PYTHON_EXE ("%%I" --version >nul 2>nul& if not errorlevel 1 set "PYTHON_EXE=%%I")
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"
exit /b 0
:install_python
where winget >nul 2>nul
if not errorlevel 1 (winget install --id Python.Python.3.13 --exact --scope user --silent --accept-package-agreements --accept-source-agreements& if not errorlevel 1 exit /b 0)
exit /b 1
:error
echo.
echo Upgrade failed.
pause
exit /b 1
