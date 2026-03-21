@echo off
chcp 65001 >nul
title TeleClinic AutoBot - Build mit Schutz
color 0B

echo.
echo ═══════════════════════════════════════════════════════════════
echo   🔐 TeleClinic AutoBot - GESCHÜTZTE Version erstellen
echo ═══════════════════════════════════════════════════════════════
echo.
echo   Diese Version enthält:
echo   ✅ Hardware-Bindung (PC-gebunden)
echo   ✅ Passwort-Aktivierung
echo   ✅ Schutz vor Weitergabe
echo.
echo   Aktivierungs-Passwort: Hanbo2001!
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
pause

echo.
echo Starte Build mit Lizenz-Schutz...
echo.

call .venv\Scripts\activate.bat
python build_portable.py

echo.
echo ═══════════════════════════════════════════════════════════════
echo   ✅ GESCHÜTZTE VERSION ERSTELLT!
echo ═══════════════════════════════════════════════════════════════
echo.
echo   WICHTIG: Diese Version ist GESCHÜTZT!
echo.
echo   Bei Installation wird Aktivierung verlangt:
echo   🔐 Passwort: Hanbo2001!
echo.
echo   Nach Aktivierung:
echo   ✅ Software ist an den spezifischen PC gebunden
echo   ✅ Weitergabe auf anderen PC funktioniert NICHT
echo   ✅ Schutz vor unbefugter Nutzung
echo.
echo   📋 Mehr Infos: SCHUTZ_VOR_WEITERGABE.md
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
pause
