@echo off
setlocal

REM TeleClinic Bot starter with basic diagnostics
set "APP_DIR=%~dp0"
set "LOG_FILE=%APP_DIR%startup_error.log"

if defined TELECLINIC_BOT_DRY_RUN (
  echo DRY RUN: ok > "%LOG_FILE%"
  exit /b 0
)

if not exist "%APP_DIR%tc_main_gui.py" (
  echo ERROR: tc_main_gui.py not found in %APP_DIR% > "%LOG_FILE%"
  echo Bitte pruefen Sie die Installation. >> "%LOG_FILE%"
  start notepad.exe "%LOG_FILE%"
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python ist nicht im PATH oder nicht installiert. > "%LOG_FILE%"
  echo Bitte installieren Sie Python und pruefen Sie die PATH-Variable. >> "%LOG_FILE%"
  start notepad.exe "%LOG_FILE%"
  exit /b 1
)

python "%APP_DIR%tc_main_gui.py"
if errorlevel 1 (
  echo.
  echo ============================================================
  echo  FEHLER: tc_main_gui.py konnte nicht gestartet werden.
  echo  Bitte schauen Sie auf die Fehlermeldung oben.
  echo ============================================================
  echo.
  pause
  exit /b 1
)

exit /b 0
