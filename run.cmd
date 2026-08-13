@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="

for %%P in (python.exe python3.exe) do (
    where %%P >nul 2>nul
    if not errorlevel 1 (
        for /f "delims=" %%I in ('where %%P 2^>nul') do (
            if not defined PYTHON_EXE (
                "%%I" --version >nul 2>nul
                if not errorlevel 1 set "PYTHON_EXE=%%I"
            )
        )
    )
)

if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"
if not defined PYTHON_EXE if exist "%ProgramFiles%\Python313\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python313\python.exe"
if not defined PYTHON_EXE if exist "%ProgramFiles%\Python314\python.exe" set "PYTHON_EXE=%ProgramFiles%\Python314\python.exe"

if not defined PYTHON_EXE (
    echo ERROR: Python was not found.
    echo Run upgrade.cmd first.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0resolve_project_builder.py" %*
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" pause
exit /b %EXITCODE%
