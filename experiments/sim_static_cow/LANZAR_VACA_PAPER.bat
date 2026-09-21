@echo off
setlocal EnableExtensions

rem Cow evasion scenario launcher (paper_wp1_wp2_cow):
rem - Scene prep (cow on WP1->WP2, rest hidden) is applied beforehand with
rem   Unreal\Scripts\apply_paper_wp1_wp2_cow_profile_and_save.py
rem - Unreal Editor + PIE must be running (AirTraffic Preview window).
rem - Vision targets only the cow class and records the YOLO overlay to mp4.

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "REPO_ROOT=%PROJECT_ROOT%\..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

rem Ensure system tools are reachable even when launched from Git Bash.
set "PATH=%SystemRoot%\System32;%SystemRoot%\System32\WindowsPowerShell\v1.0;%SystemRoot%\System32\Wbem;%LOCALAPPDATA%\Microsoft\WindowsApps;%PATH%"

set "PORCE_DEFAULTS_FORCE=0"
set "PORCE_SYSTEM_MODE=SIMULATION"

rem Vision: cow only
set "PORCE_VISION_TARGET_CLASS_NAMES=cow"
set "PORCE_VISION_TARGET_CLASS_FALLBACK_NAMES=cow"
set "PORCE_OBS_STATIC_CLASS_NAMES=cow"
set "PORCE_VISION_MAX_OBS_PER_FRAME=8"
set "PORCE_VISION_MIN_AGL_TO_PUBLISH_M=10.0"

rem YOLO overlay recording (the "YOLO window" video evidence)
set "PORCE_VISION_RECORD_ENABLE=1"
set "PORCE_VISION_RECORD_MAX_SECONDS=420"
set "PORCE_VISION_RECORD_PATH=%REPO_ROOT%\runs\cow_evasion\vision_yolo_cow_evasion.mp4"
set "PORCE_VISION_OVERLAY_MODE=paper"

rem YOLO debug window (live view of the same overlay)
set "PORCE_VISION_DEBUG_WINDOW=1"
set "PORCE_VISION_DEBUG_DOCK=1"
set "PORCE_VISION_DEBUG_TOPMOST=1"
set "PORCE_VISION_DEBUG_TITLE=YOLOv11 evidence"
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

rem Control loop: PIE is already streaming, take off soon after boot
set "PORCE_SIM_CONTROL_LOOP_STARTUP_DELAY_S=10.0"
set "PORCE_CONTROL_LOOP_STARTUP_DELAY_S=10.0"
set "PORCE_CONTROL_ARM_RETRY_INTERVAL_S=5.0"

set "PORCE_TEE_CAP_LINES=300"
set "PORCE_FORCE_CMD_WINDOWS=0"
set "PORCE_ALLOW_CMD_WINDOWS_FALLBACK=0"
set "PORCE_TERMINAL_KEEP_OPEN=0"
if not defined PORCE_WT_WINDOW set "PORCE_WT_WINDOW=DeepAeroTwinPORCE"
if not defined PORCE_OBSTACLE_TOKEN_PERSIST set "PORCE_OBSTACLE_TOKEN_PERSIST=0"

echo [COW] Launching SIMULATION pipeline with YOLO target=cow
call "%REPO_ROOT%\tools\launch_workflow.bat" SIMULATION
exit /b %errorlevel%
