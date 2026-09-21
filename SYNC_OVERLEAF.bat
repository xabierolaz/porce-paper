@echo off
REM Sincroniza el manuscrito canonico PORCE (paper/revision) con Overleaf 6aa92339.
REM Uso: doble clic. Para comprobar compilacion local antes de subir: SYNC_OVERLEAF.bat -Compile
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\sync_overleaf.ps1" %*
pause
