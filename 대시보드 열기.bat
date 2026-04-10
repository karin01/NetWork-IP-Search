@echo off
REM Do not pass Korean path inside call quotes. pushd resolves %%~dp0 once; then call by relative name.
pushd "%~dp0"
call run_dashboard.bat
set NWIP_ERR=%ERRORLEVEL%
popd
exit /b %NWIP_ERR%
