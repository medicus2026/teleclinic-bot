#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleClinic Bot - Professioneller Build & Installer
Erstellt .exe und Inno Setup Installer für die hardwaregebundene Erstaktivierung
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
INSTALLER_DIR = ROOT / "installer"

VERSION = "2.0.0"
APP_NAME = "TeleClinic AutoBot"

def print_section(title):
    """Drucke formatierte Überschrift"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def install_dependencies():
    """Installiere benötigte Build-Dependencies"""
    print_section("📦 Installiere Build-Dependencies")

    deps = ["pyinstaller", "Pillow"]

    for dep in deps:
        print(f"Installiere {dep}...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", dep],
            check=True,
            capture_output=True
        )

    print("✅ Dependencies installiert\n")

def collect_files():
    """Sammle alle benötigten Dateien"""
    print_section("📋 Sammle Dateien")

    files = {
        "main": ROOT / "tc_main_gui.py",
        "clicker": ROOT / "teleclinic_click_from_list_v9d.py",
        "scheduler": ROOT / "core_scheduler.py",
        "patients": ROOT / "scheduled_patients.py",
        "filters": ROOT / "filters.json",
        "logo": ROOT / "Logo_GIZ_Praxis_neu_ohne_Hintergrund.png"
    }

    missing = []
    for name, path in files.items():
        if path.exists():
            print(f"✅ {name}: {path.name}")
        else:
            print(f"❌ {name}: {path.name} FEHLT!")
            missing.append(name)

    if missing:
        print(f"\n⚠️ WARNUNG: {len(missing)} Datei(en) fehlen!")
        return False

    print()
    return True

def build_exe():
    """Baue .exe mit PyInstaller"""
    print_section("🔨 Baue TeleClinic-Bot.exe")

    # Cleanup alte Builds
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    DIST_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(exist_ok=True)

    main_script = ROOT / "tc_main_gui.py"

    # PyInstaller Argumente
    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=TeleClinic-Bot",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),

        # Icon (falls vorhanden)
        # "--icon=icon.ico",

        # Zusätzliche Dateien
        "--add-data", f"{ROOT / 'filters.json'};.",
        "--add-data", f"{ROOT / 'Logo_GIZ_Praxis_neu_ohne_Hintergrund.png'};.",
        "--add-data", f"{ROOT / 'teleclinic_click_from_list_v9d.py'};.",
        "--add-data", f"{ROOT / 'core_scheduler.py'};.",
        "--add-data", f"{ROOT / 'scheduled_patients.py'};.",

        # Hidden Imports
        "--hidden-import=tkinter",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=asyncio",
        "--hidden-import=playwright",
        "--hidden-import=playwright.async_api",
        "--hidden-import=json",
        "--hidden-import=pathlib",

        # Collect-all für wichtige Pakete
        "--collect-all=playwright",
        "--collect-all=PIL",

        str(main_script)
    ]

    try:
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        print("✅ .exe erfolgreich erstellt!")

        exe_path = DIST_DIR / "TeleClinic-Bot.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📍 Speicherort: {exe_path}")
            print(f"📦 Größe: {size_mb:.1f} MB\n")
            return True
        else:
            print("❌ .exe wurde nicht erstellt!")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Build fehlgeschlagen!")
        print(f"Error: {e.stderr}")
        return False

def create_inno_setup_script():
    """Erstelle Inno Setup Script ohne separates Installer-Passwort"""
    print_section("📝 Erstelle Installer-Script")

    INSTALLER_DIR.mkdir(exist_ok=True)

    # Inno Setup Script ohne doppelte Passwortlogik
    script_content = rf'''; TeleClinic AutoBot - Installer Script
; Erstellt mit Inno Setup
; HINWEIS: Kopierschutz erfolgt über die Erstaktivierung im Programm

#define MyAppName "{APP_NAME}"
#define MyAppVersion "{VERSION}"
#define MyAppPublisher "GIZ Praxis"
#define MyAppExeName "TeleClinic-Bot.exe"

[Setup]
AppId={{{{8A7B3C9D-1E2F-4A5B-8C9D-0E1F2A3B4C5D}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName={{autopf}}\TeleClinic-Bot
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir={str(INSTALLER_DIR)}
OutputBaseFilename=TeleClinic-Bot-Setup-v{VERSION}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=
UninstallDisplayIcon={{app}}\{{#MyAppExeName}}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{str(DIST_DIR / 'TeleClinic-Bot.exe')}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{str(ROOT / 'filters.json')}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{str(ROOT / 'Logo_GIZ_Praxis_neu_ohne_Hintergrund.png')}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{str(ROOT / 'requirements.txt')}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{str(ROOT / 'QUICK_START_GUIDE.md')}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\{{#MyAppName}}"; Filename: "{{app}}\{{#MyAppExeName}}"
Name: "{{group}}\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\{{#MyAppName}}"; Filename: "{{app}}\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel2=Dies installiert [name/ver] auf Ihrem Computer.%n%nDer Kopierschutz wird erst beim ersten Start im Programm geprüft.%n%nNach erfolgreicher Aktivierung auf diesem PC ist keine erneute Passworteingabe mehr nötig.
'''

    script_path = INSTALLER_DIR / "TeleClinic-Bot-Setup.iss"
    script_path.write_text(script_content, encoding='utf-8')

    print(f"✅ Installer-Script erstellt: {script_path}\n")
    return script_path

def check_inno_setup():
    """Prüfe ob Inno Setup installiert ist"""
    print_section("🔍 Prüfe Inno Setup")

    inno_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
    ]

    for path in inno_paths:
        if path.exists():
            print(f"✅ Inno Setup gefunden: {path}\n")
            return path

    print("❌ Inno Setup nicht gefunden!")
    print("\nBitte installieren Sie Inno Setup:")
    print("   https://jrsoftware.org/isdl.php")
    print("\nAlternativ: Nutzen Sie nur die .exe aus dem dist/ Ordner\n")
    return None

def build_installer(inno_path, script_path):
    """Baue Installer mit Inno Setup"""
    print_section("🚀 Baue Installer")

    try:
        result = subprocess.run(
            [str(inno_path), str(script_path)],
            check=True,
            capture_output=True,
            text=True
        )

        print("✅ Installer erfolgreich erstellt!")

        installer_path = INSTALLER_DIR / f"TeleClinic-Bot-Setup-v{VERSION}.exe"
        if installer_path.exists():
            size_mb = installer_path.stat().st_size / (1024 * 1024)
            print(f"📍 Speicherort: {installer_path}")
            print(f"📦 Größe: {size_mb:.1f} MB")
            print("🔐 Erstaktivierung erfolgt beim ersten Start im Programm.\n")
            return True
        else:
            print("❌ Installer wurde nicht erstellt!")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Installer-Build fehlgeschlagen!")
        print(f"Error: {e.stderr}")
        return False

def create_installation_guide():
    """Erstelle Installations-Anleitung"""
    guide_content = f"""# TeleClinic AutoBot - Installation

## 📦 Installations-Dateien

Sie haben zwei Möglichkeiten zur Installation:

### Option 1: Standalone .exe (EINFACH)
**Datei:** `dist/TeleClinic-Bot.exe`

✅ **Vorteile:**
- Keine Installation nötig
- Direkt ausführbar
- Portable (USB-Stick möglich)

❌ **Nachteile:**
- Keine automatische Desktop-Verknüpfung
- Keine Deinstallations-Routine
- Manuell alle Dateien kopieren

📋 **Anleitung:**
1. Kopiere den kompletten `dist/` Ordner auf den Zielrechner
2. Doppelklick auf `TeleClinic-Bot.exe`
3. Fertig!

---

### Option 2: Installer mit Erstaktivierung im Programm (EMPFOHLEN)
**Datei:** `installer/TeleClinic-Bot-Setup-v{VERSION}.exe`

✅ **Vorteile:**
- Professionelle Installation
- Einmalige Aktivierung nur beim ersten Start auf einem neuen PC
- Automatische Desktop-Verknüpfung
- Saubere Deinstallation
- Alle Dateien werden korrekt installiert

🔐 **Wichtig:** Das Aktivierungs-Passwort wird nur beim ersten Programmstart auf einem neuen PC benötigt.

📋 **Anleitung:**
1. Starte `TeleClinic-Bot-Setup-v{VERSION}.exe`
2. Folge den Installations-Schritten
3. Starte danach das Programm
4. Gib nur beim ersten Start auf diesem PC das Aktivierungs-Passwort ein
5. Danach sind keine weiteren Passworteingaben auf diesem PC nötig

---

## ⚙️ Systemvoraussetzungen

- **Betriebssystem:** Windows 10/11 (64-bit)
- **RAM:** Mindestens 4 GB
- **Festplatte:** 500 MB freier Speicher
- **Browser:** Google Chrome (wird automatisch installiert falls nicht vorhanden)

---

## 🚀 Erste Schritte nach Installation

1. **Chrome im Debug-Modus starten:**
   - Wird automatisch beim ersten Start gefragt

2. **Bei TeleClinic einloggen:**
   - Öffne Chrome
   - Gehe zu med.teleclinic.com
   - Logge dich ein

3. **Filter einstellen:**
   - Öffne TeleClinic AutoBot
   - Setze deine Filter (Tag, Zeit, Diagnose, etc.)

4. **START klicken:**
   - Bot beginnt zu scannen
   - Termine werden automatisch übernommen

---

## 🔐 Aktivierung / Kopierschutz

- Das Aktivierungs-Passwort wird **nicht** bei jeder Installation abgefragt
- Es wird nur beim **ersten Start auf einem neuen PC** benötigt
- Nach erfolgreicher Aktivierung startet das Programm auf diesem PC ohne erneute Passworteingabe
- Eine kopierte Installation auf einem anderen PC bleibt gesperrt

---

## 📞 Support

Bei Problemen oder Fragen:
- Schauen Sie in `QUICK_START_GUIDE.md`
- Prüfen Sie `tc_click_log.txt` für Fehler
- Kontaktieren Sie den Administrator

---

**Version:** {VERSION}  
**Build-Datum:** {datetime.now().strftime("%d.%m.%Y")}  
**Erstellt für:** GIZ Praxis
"""

    guide_path = ROOT / "INSTALLATION.md"
    guide_path.write_text(guide_content, encoding='utf-8')
    print(f"✅ Installations-Anleitung erstellt: {guide_path}\n")

def main():
    """Hauptfunktion"""
    print("\n" + "="*70)
    print(f"  🤖 TeleClinic AutoBot - Professional Build System")
    print(f"  Version: {VERSION}")
    print("="*70)

    # 1. Dependencies installieren
    install_dependencies()

    # 2. Dateien sammeln
    if not collect_files():
        print("\n⚠️ Bitte fehlende Dateien ergänzen und erneut versuchen.")
        return False

    # 3. .exe bauen
    if not build_exe():
        print("\n❌ Build fehlgeschlagen!")
        return False

    # 4. Inno Setup Script erstellen
    script_path = create_inno_setup_script()

    # 5. Installations-Anleitung erstellen
    create_installation_guide()

    # 6. Inno Setup prüfen und Installer bauen
    inno_path = check_inno_setup()

    if inno_path:
        if build_installer(inno_path, script_path):
            print_section("✅ BUILD ERFOLGREICH!")
            print("📦 Verfügbare Installations-Optionen:\n")
            print(f"1. Standalone .exe:")
            print(f"   → {DIST_DIR / 'TeleClinic-Bot.exe'}\n")
            print(f"2. Installer mit Erstaktivierung im Programm:")
            print(f"   → {INSTALLER_DIR / f'TeleClinic-Bot-Setup-v{VERSION}.exe'}")
            print("   🔐 Passwort nur beim ersten Start auf einem neuen PC erforderlich.\n")
            print(f"📋 Anleitung: INSTALLATION.md\n")
        else:
            print("\n⚠️ Installer-Build fehlgeschlagen, aber .exe ist verfügbar!")
    else:
        print_section("✅ .EXE ERFOLGREICH ERSTELLT!")
        print(f"📦 Standalone .exe verfügbar:")
        print(f"   → {DIST_DIR / 'TeleClinic-Bot.exe'}\n")
        print("💡 Tipp: Installiere Inno Setup für professionellen Installer")
        print("   https://jrsoftware.org/isdl.php\n")

    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Build abgebrochen durch Nutzer.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
