@echo off
REM =====================================================================
REM  Chrome Debug-Modus für TeleClinic Bot
REM =====================================================================
REM  Startet Chrome im Debug-Modus, damit der Bot sich verbinden kann
REM =====================================================================

echo.
echo ========================================================
echo   Chrome Debug-Modus für TeleClinic Bot
echo ========================================================
echo.
echo Chrome wird im Debug-Modus gestartet...
echo Bitte bei med.teleclinic.com einloggen.
echo.
echo Dieses Fenster kann minimiert bleiben.
echo ========================================================
echo.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\teleclinic-bot\chrome_profile"

echo Chrome gestartet. Sie können dieses Fenster jetzt schließen.
pause
