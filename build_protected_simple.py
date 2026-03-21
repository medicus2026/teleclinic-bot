#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleClinic Bot - Build mit Hardware-Schutz
Einfacher Build-Script ohne komplizierte Zeichen
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

def clean_build():
    """Cleanup alte Builds"""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    DIST_DIR.mkdir(exist_ok=True)

def build_exe():
    """Baue .exe mit PyInstaller + Lizenz-System"""
    print("\n" + "="*70)
    print("  BAUE TeleClinic-Bot MIT HARDWARE-BINDUNG")
    print("="*70 + "\n")

    main_script = ROOT / "tc_main_gui.py"

    args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=TeleClinic-Bot",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR),
        # Daten
        "--add-data", f"{ROOT / 'filters.json'};.",
        "--add-data", f"{ROOT / 'Logo_GIZ_Praxis_neu_ohne_Hintergrund.png'};.",
        "--add-data", f"{ROOT / 'teleclinic_click_from_list_v9d.py'};.",
        "--add-data", f"{ROOT / 'core_scheduler.py'};.",
        "--add-data", f"{ROOT / 'scheduled_patients.py'};.",
        "--add-data", f"{ROOT / 'license_system.py'};.",  # WICHTIG!
        # Hidden imports
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

    print("Baue .exe...")
    result = subprocess.run(args, capture_output=True, text=True)

    if result.returncode == 0:
        exe_path = DIST_DIR / "TeleClinic-Bot.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"OK .exe erstellt: {exe_path}")
            print(f"Groesse: {size_mb:.1f} MB\n")
            return True

    print("FEHLER beim Build!")
    print(result.stderr)
    return False

def create_package():
    """Erstelle ZIP-Paket mit Lizenz-System"""
    print("Erstelle ZIP-Paket...")

    package_dir = ROOT / "TeleClinic-Bot-Protected"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()

    # Kopiere Dateien
    files = [
        ("dist/TeleClinic-Bot.exe", "TeleClinic-Bot.exe"),
        ("license_system.py", "license_system.py"),
        ("filters.json", "filters.json"),
        ("Logo_GIZ_Praxis_neu_ohne_Hintergrund.png", "Logo.png"),
        ("QUICK_START_GUIDE.md", "QUICK_START_GUIDE.md"),
    ]

    for src, dest in files:
        src_path = ROOT / src
        if src_path.exists():
            shutil.copy2(src_path, package_dir / dest)
            print(f"  OK {dest}")

    # Erstelle README
    readme = f"""TeleClinic AutoBot - HARDWARE-GESCHUETZTE VERSION

VERSION: {VERSION}
DATUM: {datetime.now().strftime("%d.%m.%Y")}

WICHTIG: Diese Version ist GESCHUETZT!

HARDWARE-BINDUNG:
- Bei erster Ausfuehrung: Aktivierung erforderlich
- Passwort: Hanbo2001!
- Software wird an DIESEN PC gebunden
- Weitergabe auf anderen PC funktioniert NICHT

INSTALLATION:
1. Ordner auf Ziel-PC kopieren
2. TeleClinic-Bot.exe starten
3. Aktivierungs-Dialog erscheint
4. Passwort eingeben: Hanbo2001!
5. Fertig - Software ist aktiviert!

BEI WEITERGABE:
Wenn jemand die Software auf einen anderen PC kopiert:
- Hardware-ID stimmt nicht
- "Lizenz ist fuer einen anderen PC!"
- Programm startet NICHT
- SCHUTZ FUNKTIONIERT!

ENTHALTENE DATEIEN:
- TeleClinic-Bot.exe (Hauptprogramm)
- license_system.py (Lizenz-System)
- filters.json (Konfiguration)
- Logo.png (Praxis-Logo)

PASSWORT: Hanbo2001!

Support: Kontaktieren Sie Ihren Administrator
"""

    (package_dir / "README.txt").write_text(readme, encoding='utf-8')
    print("  OK README.txt\n")

    # Erstelle ZIP
    zip_path = ROOT / f"TeleClinic-Bot-Protected-v{VERSION}.zip"
    print(f"Erstelle ZIP...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in package_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(package_dir.parent)
                zipf.write(file, arcname)

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"OK ZIP erstellt: {zip_path}")
    print(f"Groesse: {zip_size_mb:.1f} MB\n")

    return True

def main():
    print("\n" + "="*70)
    print("  TeleClinic AutoBot - HARDWARE-GESCHUETZTE VERSION")
    print("  Passwort: Hanbo2001!")
    print("="*70)

    # PyInstaller installieren
    print("\nInstalliere PyInstaller...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "pyinstaller", "Pillow"],
        check=True,
        capture_output=True
    )
    print("OK PyInstaller installiert\n")

    # Cleanup
    clean_build()

    # Build .exe
    if not build_exe():
        print("\nFEHLER beim Build!")
        return False

    # Erstelle Paket
    if not create_package():
        print("\nFEHLER beim Paket!")
        return False

    # Erfolg
    print("="*70)
    print("  BUILD ERFOLGREICH!")
    print("="*70)
    print("\nGESCHUETZTE VERSION ERSTELLT:")
    print(f"  {ROOT / f'TeleClinic-Bot-Protected-v{VERSION}.zip'}")
    print("\nWICHTIG:")
    print("  - Enthaelt Hardware-Bindung")
    print("  - Aktivierungs-Passwort: Hanbo2001!")
    print("  - Weitergabe funktioniert NICHT")
    print("\nBereit zur Verteilung!\n")

    return True

if __name__ == "__main__":
    try:
        if not main():
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nAbgebrochen.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFEHLER: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
