@echo off
chcp 65001 >nul
title TeleClinic AutoBot - Build System
color 0A

echo.
echo ═══════════════════════════════════════════════════════════════
echo   🤖 TeleClinic AutoBot - Build System
echo ═══════════════════════════════════════════════════════════════
echo.
echo   Wählen Sie eine Build-Option:
echo.
echo   [1] Portable ZIP erstellen (EMPFOHLEN)
echo       → Kein Passwort, einfache Installation
echo       → Ergebnis: TeleClinic-Bot-Portable-v2.0.0.zip
echo.
echo   [2] Installer mit Passwort erstellen
echo       → Passwortschutz: Hanbo2001!
echo       → Benötigt: Inno Setup
echo       → Ergebnis: TeleClinic-Bot-Setup-v2.0.0.exe
echo.
echo   [3] Nur .exe erstellen (Test/Debug)
echo       → Schnell, aber unvollständig
echo       → Ergebnis: dist\TeleClinic-Bot.exe
echo.
echo   [4] Hilfe / Anleitung anzeigen
echo.
echo   [5] Beenden
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

set /p choice="Ihre Wahl (1-5): "

if "%choice%"=="1" goto portable
if "%choice%"=="2" goto installer
if "%choice%"=="3" goto exe_only
if "%choice%"=="4" goto help
if "%choice%"=="5" goto end
echo.
echo ❌ Ungültige Eingabe!
timeout /t 2 >nul
goto end

:portable
echo.
echo ═══════════════════════════════════════════════════════════════
echo   📦 Erstelle Portable ZIP-Paket...
echo ═══════════════════════════════════════════════════════════════
echo.
call .venv\Scripts\activate.bat
python build_portable.py
echo.
echo ═══════════════════════════════════════════════════════════════
echo   ✅ FERTIG!
echo ═══════════════════════════════════════════════════════════════
echo.
echo   Datei: TeleClinic-Bot-Portable-v2.0.0.zip
echo   Größe: ~63 MB
echo.
echo   NÄCHSTE SCHRITTE:
echo   1. ZIP auf USB-Stick kopieren
echo   2. Auf Ziel-PC entpacken
echo   3. TeleClinic-Bot.exe starten
echo.
echo   📋 Anleitung: BUILD_INSTALLATION_GUIDE.md
echo.
pause
goto end

:installer
echo.
echo ═══════════════════════════════════════════════════════════════
echo   🔐 Erstelle Installer mit Passwortschutz...
echo ═══════════════════════════════════════════════════════════════
echo.
echo   Prüfe Inno Setup...
echo.
if not exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    if not exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        echo ❌ Inno Setup nicht gefunden!
        echo.
        echo    Bitte installieren Sie Inno Setup:
        echo    https://jrsoftware.org/isdl.php
        echo.
        echo    Danach dieses Script erneut ausführen.
        echo.
        pause
        goto end
    )
)
echo   ✅ Inno Setup gefunden
echo.
call .venv\Scripts\activate.bat
python build_installer_pro.py
echo.
echo ═══════════════════════════════════════════════════════════════
echo   ✅ FERTIG!
echo ═══════════════════════════════════════════════════════════════
echo.
echo   Datei: installer\TeleClinic-Bot-Setup-v2.0.0.exe
echo   Passwort: Hanbo2001!
echo.
echo   NÄCHSTE SCHRITTE:
echo   1. Setup.exe auf USB-Stick kopieren
echo   2. Auf Ziel-PC starten
echo   3. Passwort eingeben: Hanbo2001!
echo   4. Installation durchführen
echo.
pause
goto end

:exe_only
echo.
echo ═══════════════════════════════════════════════════════════════
echo   🔨 Erstelle nur .exe (Test-Modus)...
echo ═══════════════════════════════════════════════════════════════
echo.
call .venv\Scripts\activate.bat
python build_portable.py
echo.
echo   Datei: dist\TeleClinic-Bot.exe
echo.
echo   ⚠️ HINWEIS: Für Produktion nutzen Sie Option 1 oder 2!
echo.
pause
goto end

:help
echo.
echo ═══════════════════════════════════════════════════════════════
echo   📚 HILFE - Build-Optionen erklärt
echo ═══════════════════════════════════════════════════════════════
echo.
echo   OPTION 1: Portable ZIP (EMPFOHLEN)
echo   ───────────────────────────────────────────────────────────
echo   + Einfach und schnell
echo   + Funktioniert ohne Installation
echo   + Portable (USB-Stick möglich)
echo   - Kein Passwortschutz
echo.
echo   VERWENDUNG:
echo   - Für schnelle Tests
echo   - Für Entwicklung
echo   - Wenn kein Passwort benötigt wird
echo.
echo.
echo   OPTION 2: Installer mit Passwort
echo   ───────────────────────────────────────────────────────────
echo   + Passwortschutz (Hanbo2001!)
echo   + Professionelle Installation
echo   + Desktop-Icon automatisch
echo   + Saubere Deinstallation
echo   - Benötigt Inno Setup
echo.
echo   VERWENDUNG:
echo   - Für Produktiv-Einsatz
echo   - Wenn Zugriff kontrolliert werden soll
echo   - Für professionelle Verteilung
echo.
echo.
echo   OPTION 3: Nur .exe
echo   ───────────────────────────────────────────────────────────
echo   + Sehr schnell
echo   - Unvollständig (Dateien fehlen)
echo   - Nicht empfohlen
echo.
echo   VERWENDUNG:
echo   - Nur für Tests/Debug
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo   📋 Ausführliche Anleitung: BUILD_INSTALLATION_GUIDE.md
echo.
pause
goto end

:end
echo.
echo   Vielen Dank! 👋
echo.
timeout /t 2 >nul
