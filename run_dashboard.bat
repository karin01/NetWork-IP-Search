@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ASCII-only file name + body: CMD on CP949 mis-reads UTF-8; Korean-named .bat breaks parsing.
REM Use this file to start the server from Google Drive paths with Korean folder names.

chcp 65001 >nul 2>&1

REM No auto UAC: VBS ShellExecute mojibakes Korean paths (run_dashboard.bat not found).
REM For full ARP scan: right-click this file - Run as administrator once.

if not exist "%~dp0app.py" (
    echo [ERROR] app.py missing next to this bat ^(folder offline or not synced^).
    echo Script dir: %~dp0
    echo Google Drive / OneDrive: mark folder offline-available and wait for sync.
    pause
    exit /b 1
)
cd /d "%~dp0"
if not exist "app.py" (
    echo [ERROR] cd to project folder failed ^(permissions or broken path^).
    echo Target: %~dp0
    pause
    exit /b 1
)
set "PROJROOT=%CD%"

reg query "HKLM\SOFTWARE\Npcap" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Npcap not found. ARP scan may fall back to ping. See https://npcap.com/
)

echo.
echo ========================================
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set "LANIP=%%a"
    set "LANIP=!LANIP: =!"
    echo   http://!LANIP!:8500
    goto :after_ip
)
:after_ip
echo   http://127.0.0.1:8500
echo ========================================
echo.
echo [INFO] Dashboard: browser = UI, this CMD = server logs only. Build wifi17. Wi-Fi-only page:
echo        http://127.0.0.1:8500/wifi
echo        Stale UI? Open http://127.0.0.1:8500/api/nwip-whoami
echo        build-info: template_has_wifi_cta = main has Wi-Fi+iperf cards; wifi_panels_has_analyzer = true.
echo [INFO] Live Map (Streamlit, separate from Flask): cd network_ops ^&^& streamlit run live_map_dashboard.py
echo        Usually http://127.0.0.1:8501 — uses live_map/hosts.yaml, NOT this Flask page.
echo.

set "PYEXE=python"
if exist "%PROJROOT%\.venv\Scripts\python.exe" (
  set "PYEXE=%PROJROOT%\.venv\Scripts\python.exe"
  echo [INFO] Using venv Python: !PYEXE!
)

where python >nul 2>&1
if errorlevel 1 (
    if not exist "%PROJROOT%\.venv\Scripts\python.exe" (
      echo [ERROR] python not found in PATH.
      pause
      exit /b 1
    )
)

"%PYEXE%" "%PROJROOT%\check_dashboard_template.py"
if errorlevel 1 (
    echo [ERROR] check_dashboard_template.py failed. Sync this folder or fix templates.
    pause
    exit /b 1
)

echo.
echo [INFO] After server starts: http://127.0.0.1:8500/api/nwip-whoami  ^(then /api/build-info^)
echo [WARN] If whoami shows 404: another app may already use port 8500, or wrong folder.
echo        Check LISTENING lines below ^(then close that PID in Task Manager or use set NETWORK_IP_SEARCH_PORT=8501^):
netstat -ano | findstr ":8500"
echo.

REM WHY: Nested quotes break when PROJROOT has spaces (Korean path). START /D sets CWD; pass app.py as relative name only.
start "NetWork-IP Flask 8500" /D "%PROJROOT%" cmd /k ""%PYEXE%" app.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8500/api/nwip-whoami"
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:8500/?nocache=1"

echo Browser opened. Flask runs in the cmd window titled NetWork-IP Flask 8500.
pause
endlocal
