#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleClinic Bot - Einfacher Build (nur .exe)
Für Systeme ohne Inno Setup
"""

import subprocess
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
VERSION = "2.0.0"

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def build_exe():
    """Baue .exe mit PyInstaller"""
    print_header("🔨 Baue TeleClinic-Bot.exe")

    # Cleanup
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    DIST_DIR.mkdir(exist_ok=True)

    # PyInstaller
    main_script = ROOT / "tc_main_gui.py"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=TeleClinic-Bot",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        "--add-data", f"{ROOT / 'filters.json'};.",
        "--add-data", f"{ROOT / 'Logo_GIZ_Praxis_neu_ohne_Hintergrund.png'};.",
        "--add-data", f"{ROOT / 'teleclinic_click_from_list_v9d.py'};.",
        "--add-data", f"{ROOT / 'core_scheduler.py'};.",
        "--add-data", f"{ROOT / 'scheduled_patients.py'};.",
        "--add-data", f"{ROOT / 'license_system.py'};.",  # WICHTIG: Lizenz-System!
        "--hidden-import=tkinter",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--hidden-import=asyncio",
        "--hidden-import=playwright",
        "--hidden-import=hashlib",
        "--hidden-import=platform",
        "--hidden-import=subprocess",
        "--hidden-import=uuid",
        "--collect-all=playwright",
        "--collect-all=PIL",
        str(main_script)
    ]

    print("Starte PyInstaller...")
    result = subprocess.run(args, capture_output=True, text=True)

    if result.returncode == 0:
        exe_path = DIST_DIR / "TeleClinic-Bot.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ .exe erstellt: {exe_path}")
            print(f"📦 Größe: {size_mb:.1f} MB\n")
            return True

    print("❌ Build fehlgeschlagen!")
    print(result.stderr)
    return False

def create_portable_package():
    """Erstelle portables ZIP-Paket"""
    print_header("📦 Erstelle portables Installations-Paket")

    package_dir = ROOT / "TeleClinic-Bot-Portable"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()

    # Kopiere Dateien
    files_to_copy = [
        ("dist/TeleClinic-Bot.exe", "TeleClinic-Bot.exe"),
        ("filters.json", "filters.json"),
        ("Logo_GIZ_Praxis_neu_ohne_Hintergrund.png", "Logo.png"),
        ("QUICK_START_GUIDE.md", "QUICK_START_GUIDE.md"),
        ("requirements.txt", "requirements.txt"),
        ("license_system.py", "license_system.py"),  # WICHTIG: Für Hardware-Bindung!
    ]

    for src, dest in files_to_copy:
        src_path = ROOT / src
        if src_path.exists():
            shutil.copy2(src_path, package_dir / dest)
            print(f"✅ Kopiert: {dest}")

    # Erstelle README
    readme_content = f"""# TeleClinic AutoBot - Portable Version mit PC-Bindung

## 🔐 WICHTIG: Diese Version ist geschützt

Diese Software nutzt **Hardware-Bindung** zum Schutz vor unbefugter Weitergabe:
- Beim ersten Start auf einem neuen PC: Aktivierung erforderlich
- Danach auf diesem PC: keine erneute Passwortabfrage
- Die Lizenz wird an **diesen PC** gebunden
- Kopie auf anderen PC: funktioniert nicht

---

## 🚀 Installation (4 Schritte)

### Schritt 1: Dateien kopieren
Kopiere diesen kompletten Ordner auf den Zielrechner
(z.B. nach C:\\Programme\\TeleClinic-Bot oder Desktop)

### Schritt 2: Chrome installieren (falls nicht vorhanden)
- Lade Chrome herunter: https://www.google.com/chrome/
- Installiere Chrome

### Schritt 3: Programm starten
- Doppelklick auf `TeleClinic-Bot.exe`
- Beim **ersten Start auf diesem PC** erscheint der Aktivierungs-Dialog

### Schritt 4: Einmalig aktivieren
- Gib das Aktivierungs-Passwort ein: `Hanbo2001!`
- Danach ist die Software für **diesen PC** freigeschaltet
- Weitere Starts auf demselben PC benötigen **kein Passwort mehr**

---

## 🛡️ Schutz vor Weitergabe

Wenn jemand diese Software auf einen **anderen PC** kopiert:
1. Software startet
2. Hardware-ID wird geprüft
3. ❌ Lizenz passt nicht zu diesem PC
4. Programm startet nicht

→ **Schutz funktioniert**

---

## 🔧 Wichtige Hinweise

### Bei Hardware-Änderungen:
- Neuer RAM / neue Grafikkarte: meist unkritisch
- Neues Motherboard / neue CPU: neue Aktivierung kann nötig sein

### Lizenz-Datei:
- Die Lizenz wird nach Aktivierung **PC-lokal** gespeichert
- Sie muss nicht im Programmordner liegen
- Löschen der lokalen Lizenzdaten kann eine neue Aktivierung erforderlich machen

---

## 📋 Enthaltene Dateien

- `TeleClinic-Bot.exe` (Hauptprogramm)
- `license_system.py` (Lizenz-System)
- `filters.json` (Standard-Filter)
- `Logo.png` (Praxis-Logo)
- `QUICK_START_GUIDE.md` (Ausführliche Anleitung)

---

## ⚙️ Systemvoraussetzungen

- Windows 10/11 (64-bit)
- 4 GB RAM (empfohlen: 8 GB)
- 500 MB freier Speicher
- Google Chrome Browser

---

## 💡 Desktop-Verknüpfung erstellen

1. Rechtsklick auf `TeleClinic-Bot.exe`
2. "Senden an" → "Desktop (Verknüpfung erstellen)"
3. Fertig

---

## 🔐 Aktivierungs-Passwort

**Aktivierungs-Passwort:** `Hanbo2001!`

Bitte nur an autorisierte Personen weitergeben.

---

## 📞 Support

Bei Fragen kontaktieren Sie Ihren Administrator.

**Version:** {VERSION}
**Build-Datum:** {datetime.now().strftime("%d.%m.%Y")}
**Lizenz-Typ:** Hardware-gebunden (PC-spezifisch)
"""

    (package_dir / "README.txt").write_text(readme_content, encoding='utf-8')
    print(f"✅ README erstellt\n")

    # Erstelle ZIP
    zip_path = ROOT / f"TeleClinic-Bot-Portable-v{VERSION}.zip"
    print(f"Erstelle ZIP-Archiv...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in package_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(package_dir.parent)
                zipf.write(file, arcname)

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"✅ ZIP erstellt: {zip_path}")
    print(f"📦 Größe: {zip_size_mb:.1f} MB\n")

    return True

def main():
    print("\n" + "="*70)
    print(f"  🤖 TeleClinic AutoBot - Einfacher Build")
    print(f"  Version: {VERSION}")
    print("="*70)

    print("\n📦 Installiere PyInstaller...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "pyinstaller", "Pillow"],
        check=True,
        capture_output=True
    )
    print("✅ PyInstaller installiert\n")

    # Build .exe
    if not build_exe():
        print("\n❌ Build fehlgeschlagen!")
        return False

    # Erstelle portables Paket
    if not create_portable_package():
        print("\n⚠️ Paket-Erstellung fehlgeschlagen!")
        return False

    # Zusammenfassung
    print_header("✅ BUILD ERFOLGREICH!")
    print("📦 Verfügbare Dateien:\n")
    print(f"1. Einzelne .exe:")
    print(f"   {DIST_DIR / 'TeleClinic-Bot.exe'}\n")
    print(f"2. Portables Paket (ZIP):")
    print(f"   {ROOT / f'TeleClinic-Bot-Portable-v{VERSION}.zip'}\n")
    print("💡 Für Installer mit zusätzlichem Setup-Komfort: Nutze build_installer_pro.py\n")

    return True

if __name__ == "__main__":
    try:
        if not main():
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Build abgebrochen.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

