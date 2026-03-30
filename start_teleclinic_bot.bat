@echo off
setlocal

REM TeleClinic Bot Starter
set "APP_DIR=%~dp0"
set "LOG_FILE=%APP_DIR%startup_error.log"

if defined TELECLINIC_BOT_DRY_RUN (
  echo DRY RUN: ok > "%LOG_FILE%"
  exit /b 0
)

if not exist "%APP_DIR%tc_main_gui.py" (
  echo ERROR: tc_main_gui.py nicht gefunden in %APP_DIR% > "%LOG_FILE%"
  start notepad.exe "%LOG_FILE%"
  exit /b 1
)

REM Bevorzuge venv-Python falls vorhanden
set "PYTHON_EXE="
if exist "%APP_DIR%.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%APP_DIR%.venv\Scripts\python.exe"
) else (
  where python >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_EXE=python"
  )
)

if "%PYTHON_EXE%"=="" (
  echo ERROR: Python nicht gefunden. Bitte Python installieren oder venv einrichten. > "%LOG_FILE%"
  start notepad.exe "%LOG_FILE%"
  exit /b 1
)

cd /d "%APP_DIR%"
"%PYTHON_EXE%" "%APP_DIR%tc_main_gui.py"
if errorlevel 1 (
  echo.
  echo ============================================================
  echo  FEHLER beim Starten. Bitte Fehlermeldung oben pruefen.
  echo ============================================================
  echo.
  pause
  exit /b 1
)

exit /b 0
