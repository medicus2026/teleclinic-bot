# 📁 TeleClinic Bot - Finale Projektstruktur

## ✅ Aufgeräumt am 2026-01-25

### 🎯 Core-Dateien (PRODUKTIV)

#### **Programme:**
- `teleclinic_click_from_list_v9d.py` - Scanner & Clicker (Hauptlogik)
- `tc_main_gui.py` - Haupt-GUI mit allen Filtern
- `core_scheduler.py` - Terminplanung & Scheduler

#### **Konfiguration:**
- `filters.json` - Filter-Einstellungen (von GUI erstellt/bearbeitet)
- `scheduled_slots.json` - Gebuchte Termine (automatisch)

#### **Build & Installation:**
- `build_exe.py` - Build-Script für .exe
- `BUILD_INSTALLER.bat` - Batch-Script für Windows
- `requirements.txt` - Python-Dependencies

#### **Dokumentation:**
- `INSTALLER_README.md` - Installations-Anleitung
- `HYBRID_SYSTEM_INFO.md` - Technische Dokumentation

#### **Output:**
- `dist/TeleClinic-Bot.exe` - Fertige Windows-Anwendung
- `tc_click_log.txt` - Live-Log

---

## 🗑️ Gelöscht (40 Dateien)

### Alte Versionen:
- ❌ teleclinic_autorunner_v3.2_fullscan_refined.py
- ❌ filters_gui_v3_headlessaware.py
- ❌ tc_gui.py, tc_start_with_gui.py
- ❌ tc_filters.py, tc_filter_check.py, tc_utils.py

### Test-Dateien:
- ❌ test_complete_flow.py, test_card_text.py
- ❌ find_card_structure.py, find_haut_case.py
- ❌ diagnose_aktuell.py, monitor_bot.py

### Alte Dokumentation:
- ❌ 13x .md Dateien (AKTUELLE_KONFIGURATION, ANLEITUNG_MIT_GUI, etc.)

### Alte Batch/Scripts:
- ❌ QUICK_START.bat, START_MIT_GUI.bat, etc.
- ❌ start_chrome_debug.bat/.ps1

### Alte Logs/Configs:
- ❌ tc_config.yaml, tc_state.json
- ❌ tc_runner_log.txt, tc_test_flow_log.txt
- ❌ stop.flag, README.txt, tc_scans/

---

## 📂 System-Ordner (automatisch erstellt/verwaltet)

- `.venv/` oder `venv/` - Python Virtual Environment
- `build/` - PyInstaller Build-Cache
- `chrome_profile/` - Chrome Debug-Profil
- `logs/`, `backup/` - Logs & Backups
- `__pycache__/`, `.idea/` - Python/IDE Cache

---

## 🚀 Workflow

### Entwicklung:
1. Code ändern in: `teleclinic_click_from_list_v9d.py` oder `tc_main_gui.py`
2. Build: `python build_exe.py`
3. Testen: `dist/TeleClinic-Bot.exe`

### Verteilung:
1. Kopiere `dist/` Ordner auf anderen PC
2. Doppelklick auf `TeleClinic-Bot.exe`
3. Filter einstellen → START

### Filter anpassen (ohne Neu-Build):
1. Öffne `TeleClinic-Bot.exe`
2. Ändere Filter in GUI
3. Klick "Filter speichern"

---

## 📊 Statistik

- **Produktiv-Dateien:** 12
- **Dokumentation:** 2
- **Entfernt:** 40
- **Größe dist/:** ~100 MB (inkl. Python + Playwright)

---

**Stand:** 2026-01-25  
**Version:** 1.0 (Production-Ready)
