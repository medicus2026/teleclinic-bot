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
  > "%LOG_FILE%" echo ERROR: tc_main_gui.py nicht gefunden in %APP_DIR%
  start "" notepad.exe "%LOG_FILE%"
  exit /b 1
)

REM 1) Bevorzuge strikt venv-Python (damit Pillow/PIL sicher vorhanden ist)
set "PYTHON_CMD="
if exist "%APP_DIR%.venv\Scripts\python.exe" (
  set "PYTHON_CMD=%APP_DIR%.venv\Scripts\python.exe"
)

REM 2) Fallback: py -3
if "%PYTHON_CMD%"=="" (
  where py >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
  )
)

REM 3) Fallback: python aus PATH
if "%PYTHON_CMD%"=="" (
  where python >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_CMD=python"
  )
)

if "%PYTHON_CMD%"=="" (
  > "%LOG_FILE%" echo ERROR: Kein Python gefunden. Bitte .venv oder Python installieren.
  start "" notepad.exe "%LOG_FILE%"
  exit /b 1
)

pushd "%APP_DIR%"
REM GUI direkt starten - kein stdout-Redirect, damit das Fenster sichtbar bleibt
"%PYTHON_CMD%" "%APP_DIR%tc_main_gui.py"
set "RC=%ERRORLEVEL%"
popd

if not "%RC%"=="0" (
  > "%LOG_FILE%" echo FEHLER beim Starten. Exit-Code: %RC%
  start "" notepad.exe "%LOG_FILE%"
  exit /b %RC%
)

exit /b 0
