@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "REPO_ROOT=%PROJECT_ROOT%\..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
set "SRC_DIR=%REPO_ROOT%\src"
set "RUN_LOGS=%REPO_ROOT%\runs\logs\cow_evasion_run"
if not exist "%RUN_LOGS%" mkdir "%RUN_LOGS%"

set "PATH=%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0;%SystemRoot%\System32\Wbem;%LOCALAPPDATA%\Microsoft\WindowsApps;%PATH%"

set "PORCE_DEFAULTS_FORCE=0"
set "PORCE_SYSTEM_MODE=SIMULATION"

rem Waypoints file for cow evasion
set "PORCE_WAYPOINTS_FILE=%REPO_ROOT%\missions\cow_evasion_545m.waypoints"

rem Vision: cow only (SENSITIVE PARAMETERS)
set "PORCE_VISION_TARGET_CLASS_NAMES=cow"
set "PORCE_VISION_TARGET_CLASS_FALLBACK_NAMES=cow"
set "PORCE_OBS_STATIC_CLASS_NAMES=cow"
set "PORCE_VISION_MAX_OBS_PER_FRAME=8"
set "PORCE_VISION_MIN_AGL_TO_PUBLISH_M=10.0"
set "PORCE_VISION_DET_CONF=0.05"
set "PORCE_VISION_PUBLISH_CONF=0.25"
set "PORCE_VISION_MIN_BOX_HEIGHT_PX=4.0"
set "PORCE_VISION_MIN_BOX_AREA_FRAC=0.000050"
set "PORCE_VISION_MAX_BOX_AREA_FRAC_COW=0.500"

rem YOLO overlay recording (the "YOLO window" video evidence)
set "PORCE_VISION_RECORD_ENABLE=1"
set "PORCE_VISION_RECORD_MAX_SECONDS=90"
set "PORCE_VISION_RECORD_PATH=%REPO_ROOT%\runs\cow_evasion\vision_yolo_cow_evasion_final.mp4"
set "PORCE_VISION_OVERLAY_MODE=paper"

rem YOLO debug window (live view of the same overlay)
set "PORCE_VISION_DEBUG_WINDOW=1"
set "PORCE_VISION_DEBUG_DOCK=1"
set "PORCE_VISION_DEBUG_TOPMOST=1"
set "PORCE_VISION_DEBUG_TITLE=YOLOv11 - Cow Evasion"
set "PORCE_VISION_PROCESS_PRIORITY=high"

rem Telemetry smoothing (same as canonical paper launcher)
set "PORCE_TELEMETRY_YAW_SMOOTH_ENABLE=1"
set "PORCE_TELEMETRY_YAW_SMOOTH_MAX_RATE_DPS=30.0"
set "PORCE_TELEMETRY_YAW_SMOOTH_TAU_S=0.65"
set "PORCE_TELEMETRY_ATTITUDE_SMOOTH_ENABLE=1"
set "PORCE_TELEMETRY_ATTITUDE_SMOOTH_MAX_RATE_DPS=45.0"
set "PORCE_TELEMETRY_ATTITUDE_SMOOTH_TAU_S=0.50"

rem Capture of the PIE window
set "PORCE_CAPTURE_WINDOW_TITLE=AirTraffic Preview"
set "PORCE_CAPTURE_WINDOW_CLASS=UnrealWindow"
set "PORCE_CAPTURE_WINDOW_EXACT=0"
set "PORCE_CAPTURE_WINDOW_METHOD=printwindow"
set "PORCE_CAPTURE_WINDOW_FOCUS=0"
set "PORCE_CAPTURE_WINDOW_CLICK_FOCUS=0"
set "PORCE_CAPTURE_WINDOW_TOPMOST=0"

rem Control loop: PIE is already streaming, but give YOLO time to load before takeoff.
set "PORCE_SIM_CONTROL_LOOP_STARTUP_DELAY_S=40.0"
set "PORCE_CONTROL_LOOP_STARTUP_DELAY_S=40.0"
set "PORCE_CONTROL_ARM_RETRY_INTERVAL_S=5.0"

rem Audit session folder (without this, AUDIT_ROOT resolves to ".").
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "PORCE_RUN_TS=%%i"
set "PORCE_AUDIT_ROOT=%REPO_ROOT%\runs\zero_trust\%PORCE_RUN_TS%_cow_evasion"

set "PORCE_TEE_CAP_LINES=300"
if not defined PORCE_OBSTACLE_TOKEN_PERSIST set "PORCE_OBSTACLE_TOKEN_PERSIST=0"
if not defined PORCE_OBSTACLE_TOKEN_REQUIRED set "PORCE_OBSTACLE_TOKEN_REQUIRED=1"

rem Shared obstacle token for this run (brain validates, vision sends).
for /f %%i in ('powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')"') do set "PORCE_OBSTACLE_TOKEN=%%i"
set "PORCE_UNREAL_TELEMETRY_TOKEN=%PORCE_OBSTACLE_TOKEN%"
set "PORCE_UNREAL_TWIN_TOKEN=%PORCE_OBSTACLE_TOKEN%"

rem Load remaining defaults (keeps values set above).
call "%REPO_ROOT%\tools\load_porce_defaults.bat" "%SRC_DIR%\configs\porce_defaults.env" 0 || exit /b 5

set "PY=%PORCE_PYTHON%"
if not defined PY if exist "%REPO_ROOT%\..\venv\Scripts\python.exe" set "PY=%REPO_ROOT%\..\venv\Scripts\python.exe"
if not defined PY set "PY=python"

echo [COW_EVASION] Starting MASTER LOG...
start "PORCE MASTER LOG" /min cmd /c "cd /d "%SRC_DIR%" && "%PY%" -u log_server.py > "%RUN_LOGS%\log_server.out.log" 2>&1"
timeout /t 3 /nobreak >nul

echo [COW_EVASION] Starting SITL (WSL)...
start "PORCE SITL" /min cmd /c "cd /d "%SRC_DIR%" && "%PY%" -u sitl_runner.py --prefix SITL --cap-lines 300 > "%RUN_LOGS%\sitl.out.log" 2>&1"
timeout /t 10 /nobreak >nul

echo [COW_EVASION] Starting BRAIN...
start "PORCE BRAIN" /min cmd /c "cd /d "%SRC_DIR%" && set PORCE_SYSTEM_MODE=SIMULATION && "%PY%" -u flight_controller.py > "%RUN_LOGS%\brain.out.log" 2>&1"
timeout /t 5 /nobreak >nul

echo [COW_EVASION] Starting EYES (YOLO)...
start "PORCE EYES" /min cmd /c "cd /d "%SRC_DIR%" && set PORCE_SYSTEM_MODE=SIMULATION && "%PY%" -u vision_system.py > "%RUN_LOGS%\vision.out.log" 2>&1"
timeout /t 3 /nobreak >nul

echo [COW_EVASION] Starting VIZ...
start "PORCE VIZ" /min cmd /c "cd /d "%SRC_DIR%" && "%PY%" -u viz_recorder.py > "%RUN_LOGS%\viz.out.log" 2>&1"

echo [COW_EVASION] All components launched. Logs: %RUN_LOGS%
exit /b 0
