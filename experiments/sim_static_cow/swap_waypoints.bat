@echo off
setlocal EnableExtensions

set "PROJECT_ROOT=%~dp0"
set "REPO_ROOT=%PROJECT_ROOT%\..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
set "MISSIONS_DIR=%REPO_ROOT%\missions"
set "BACKUP_DIR=%REPO_ROOT%\runs\waypoints_backup"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
set "WAYPOINTS_FILE=%MISSIONS_DIR%\ejea_canonical_523m.waypoints"
set "BACKUP_FILE=%BACKUP_DIR%\ejea_canonical_523m.waypoints.backup"
set "COW_EVASION_FILE=%MISSIONS_DIR%\cow_evasion_545m.waypoints"

if /I "%~1"=="cow_evasion" (
    echo [SWAP] Switching to cow_evasion waypoints...
    
    rem Backup original if not exists
    if not exist "%BACKUP_FILE%" (
        echo [SWAP] Creating backup: %BACKUP_FILE%
        copy /Y "%WAYPOINTS_FILE%" "%BACKUP_FILE%" >nul
    )
    
    rem Copy cow_evasion waypoints
    echo [SWAP] Copying: %COW_EVASION_FILE% -^> %WAYPOINTS_FILE%
    copy /Y "%COW_EVASION_FILE%" "%WAYPOINTS_FILE%" >nul
    echo [SWAP] Done. Using cow_evasion waypoints.
    
) else if /I "%~1"=="ejea" (
    echo [SWAP] Switching to ejea waypoints...
    
    rem Restore backup
    if exist "%BACKUP_FILE%" (
        echo [SWAP] Restoring: %BACKUP_FILE% -^> %WAYPOINTS_FILE%
        copy /Y "%BACKUP_FILE%" "%WAYPOINTS_FILE%" >nul
        echo [SWAP] Done. Using ejea waypoints.
    ) else (
        echo [SWAP] ERROR: Backup not found: %BACKUP_FILE%
        exit /b 1
    )
    
) else (
    echo Usage: %0 {cow_evasion^|ejea}
    echo.
    echo   cow_evasion  - Use cow_evasion_545m.waypoints (45m AGL)
    echo   ejea         - Use ejea_canonical_523m.waypoints (23m AGL)
    exit /b 1
)

exit /b 0
