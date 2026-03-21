#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build-Script für TeleClinic Bot als .exe
Erstellt eine standalone Windows-Anwendung mit PyInstaller
"""

import subprocess
import sys
import os
from pathlib import Path
try:
    import PyInstaller.__main__ as pyinstaller_main
except ImportError:
    pyinstaller_main = None

ROOT = Path(__file__).resolve().parent

def install_pyinstaller():
    """Installiere PyInstaller falls nicht vorhanden"""
    print("📦 Installiere PyInstaller...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-U", "pyinstaller", "Pillow"],
                   check=True)

def build_exe():
    """Baue .exe mit PyInstaller"""
    print("🔨 Baue TeleClinic Bot .exe...")

    # Sammel alle Python-Dateien die gebraucht werden
    main_script = ROOT / "tc_main_gui.py"
    click_script = ROOT / "teleclinic_click_from_list_v9d.py"

    if not main_script.exists():
        print(f"❌ Datei nicht gefunden: {main_script}")
        return False

    if pyinstaller_main is None:
        print("❌ PyInstaller konnte nicht importiert werden. Bitte neu installieren.")
        return False

    args = [
        "--onefile",
        "--windowed",
        "--icon=NONE",
        "--name=TeleClinic-Bot",
        "--distpath=./dist",
        "--workpath=./build",
        "--specpath=./build",
        "--add-data", f"{ROOT}/filters.json;.",
        "--hidden-import=tkinter",
        "--hidden-import=asyncio",
        "--hidden-import=playwright",
        "--hidden-import=json",
        str(main_script)
    ]

    try:
        pyinstaller_main.run(args)
        print("✅ .exe erfolgreich erstellt!")
        print(f"📍 Speicherort: {ROOT}/dist/TeleClinic-Bot.exe")
        return True
    except Exception as e:
        print(f"❌ Fehler beim Build: {e}")
        return False

def create_desktop_shortcut():
    """Erstelle Desktop-Shortcut (Windows-spezifisch)"""
    print("🖥️ Erstelle Desktop-Shortcut...")

    import ctypes
    from pathlib import Path

    exe_path = ROOT / "dist" / "TeleClinic-Bot.exe"

    if not exe_path.exists():
        print(f"⚠️ .exe nicht gefunden: {exe_path}")
        return False

    try:
        # Desktop-Pfad
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "TeleClinic-Bot.lnk"

        # Windows-API für Shortcut (Shell.CreateShortcut)
        shell = ctypes.windll.shell32
        shell.ShellExecuteW(None, "open",
                          f'powershell -Command "& {{{shell}}}'
                          f'$WshShell = New-Object -ComObject WScript.Shell;'
                          f'$Shortcut = $WshShell.CreateShortcut(\'{shortcut_path}\');'
                          f'$Shortcut.TargetPath = \'{exe_path}\';'
                          f'$Shortcut.Save()"',
                          None, None, 1)

        print(f"✅ Shortcut erstellt: {shortcut_path}")
        return True
    except Exception as e:
        print(f"⚠️ Shortcut-Erstellung fehlgeschlagen: {e}")
        print("   Du kannst manuell einen Shortcut erstellen (Rechtsklick auf .exe → Senden an → Desktop)")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 TeleClinic Bot - Build für Windows .exe")
    print("=" * 80)
    print()

    # PyInstaller installieren
    install_pyinstaller()
    print()

    # Build .exe
    if build_exe():
        print()
        create_desktop_shortcut()
        print()
        print("=" * 80)
        print("✅ FERTIG! TeleClinic-Bot.exe wurde erstellt.")
        print(f"📍 Speicherort: {ROOT}/dist/TeleClinic-Bot.exe")
        print("=" * 80)
    else:
        print()
        print("❌ Build fehlgeschlagen.")
        sys.exit(1)
