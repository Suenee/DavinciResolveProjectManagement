@echo off
setlocal
call "%~dp0run.cmd" --diagnose
exit /b %ERRORLEVEL%
