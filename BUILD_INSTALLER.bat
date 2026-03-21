@echo off
REM TeleClinic Bot - Build & Installation Script
setlocal enabledelayedexpansion

echo.
echo ==============================================================================
echo   TeleClinic Bot - Windows Installer Builder
echo ==============================================================================
echo.

REM Prüfe Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python ist nicht installiert oder nicht im PATH!
    echo.
    echo Bitte installiere Python 3.10+ von https://www.python.org
    echo Achte darauf, "Add Python to PATH" anzuhaken!
    pause
    exit /b 1
)

echo [OK] Python gefunden.
echo.

REM Installiere PyInstaller und Playwright
echo [INFO] Installiere PyInstaller und Playwright...
python -m pip install -U pyinstaller Pillow playwright
if errorlevel 1 (
    echo [ERROR] Installation von Abhängigkeiten fehlgeschlagen!
    pause
    exit /b 1
)

echo [OK] Abhängigkeiten installiert.
echo.

REM Installiere Playwright-Browser
playwright install
if errorlevel 1 (
    echo [ERROR] Playwright-Browser-Installation fehlgeschlagen!
    pause
    exit /b 1
)

echo [OK] Playwright-Browser installiert.
echo.

REM Baue EXE
set OUTPUT_DIR=C:\teleclinic-bot
python build_exe.py --distpath %OUTPUT_DIR% --workpath %OUTPUT_DIR% --specpath %OUTPUT_DIR%
if errorlevel 1 (
    echo [ERROR] Build fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ==============================================================================
echo   [SUCCESS] TeleClinic Bot wurde erfolgreich gebaut!
echo ==============================================================================
echo.
echo Speicherort: %OUTPUT_DIR%\TeleClinic-Bot.exe
echo.
echo [NEXT STEPS]
echo 1. Kopiere den Ordner "C:\teleclinic-bot" auf andere PCs
echo 2. Starte TeleClinic-Bot.exe
echo 3. GUI öffnet sich automatisch
echo.
pause

REM Lizenzprüfung
echo [INFO] Führe Lizenzprüfung durch...
python license_system.py
if errorlevel 1 (
    echo [ERROR] Lizenzprüfung fehlgeschlagen!
    pause
    exit /b 1
)

echo [OK] Lizenzprüfung erfolgreich.
echo.

REM GUI nach Installation starten
echo [INFO] Starte GUI nach Installation...
start TeleClinic-Bot.exe
if errorlevel 1 (
    echo [ERROR] GUI konnte nicht gestartet werden!
    pause
    exit /b 1
)

echo [OK] GUI erfolgreich gestartet.
echo.

REM Überprüfen, ob wmic verfügbar ist
where wmic >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Der Befehl "wmic" ist nicht verfügbar. Bitte stellen Sie sicher, dass wmic installiert ist oder verwenden Sie eine alternative Methode zur Hardware-Identifikation.
    pause
    exit /b 1
)

echo [OK] wmic ist verfügbar.
echo.
