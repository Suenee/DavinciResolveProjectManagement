@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHON_EXE="
for %%P in (python.exe python3.exe) do if not defined PYTHON_EXE for /f "delims=" %%I in ('where %%P 2^>nul') do ("%%I" --version >nul 2>nul && set "PYTHON_EXE=%%I")
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_EXE (echo ERROR: Python was not found.& echo Run upgrade.cmd first.& pause& exit /b 1)
"%PYTHON_EXE%" "%~dp0resolve_gui.py"
exit /b %ERRORLEVEL%
