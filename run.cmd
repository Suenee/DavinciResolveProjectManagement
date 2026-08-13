@echo off
setlocal
python "%~dp0resolve_project_builder.py" %*
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" pause
exit /b %EXITCODE%
