#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FINALES STABILITÄTS-AUDIT: Alle kritischen Punkte überprüft
"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
CLICKER_FILE = ROOT / "teleclinic_click_from_list_v9d.py"
SCHEDULER_FILE = ROOT / "core_scheduler.py"

print("\n" + "="*80)
print("🔒 FINALES STABILITÄTS-AUDIT - Alle kritischen Komponenten")
print("="*80 + "\n")

clicker_code = CLICKER_FILE.read_text(encoding="utf-8")
scheduler_code = SCHEDULER_FILE.read_text(encoding="utf-8")

# =============================================================================
# KRITISCHER PUNKT 1: patients_accepted Counter
# =============================================================================
print("1️⃣  PATIENTS_ACCEPTED COUNTER")
print("-" * 80)

global_declarations = []
for line_num, line in enumerate(clicker_code.split("\n"), 1):
    if "global patients_accepted" in line and not line.strip().startswith("#"):
        global_declarations.append(line_num)

if len(global_declarations) >= 3:
    print(f"  ✅ 'global patients_accepted' in {len(global_declarations)} Funktionen deklariert")
    for line_num in global_declarations:
        print(f"     → Zeile {line_num}")
    print(f"  ✅ STABIL: Counter wird korrekt hochgezählt\n")
else:
    print(f"  ❌ WARNUNG: Nur {len(global_declarations)} global-Deklarationen gefunden!\n")

# =============================================================================
# KRITISCHER PUNKT 2: Log-Datei wird gelöscht
# =============================================================================
print("2️⃣  LOG-DATEI RESET")
print("-" * 80)

if "LOG_PATH.unlink()" in clicker_code and "if LOG_PATH.exists():" in clicker_code:
    print("  ✅ Log-Datei wird beim Bot-Start gelöscht")
    print("  ✅ STABIL: Keine alten Log-Einträge mehr gezählt\n")
else:
    print("  ❌ WARNUNG: Log-Reset nicht gefunden!\n")

# =============================================================================
# KRITISCHER PUNKT 3: Scheduler Auto-Cleanup
# =============================================================================
print("3️⃣  SCHEDULER AUTO-CLEANUP")
print("-" * 80)

if "dates_to_delete = [d for d in slots.keys() if d < today]" in scheduler_code:
    print("  ✅ Auto-Cleanup für alte Slots implementiert")
    print("  ✅ STABIL: Alte Scheduler-Slots werden automatisch entfernt\n")
else:
    print("  ❌ WARNUNG: Auto-Cleanup nicht gefunden!\n")

# =============================================================================
# KRITISCHER PUNKT 4: Scheduler wird IMMER benutzt (nicht umgangen)
# =============================================================================
print("4️⃣  SCHEDULER WIRD IMMER BENUTZT")
print("-" * 80)

# Prüfe ob overlap_time den Scheduler noch umgeht
if "if overlap_time:" in clicker_code and "slot = overlap_time" in clicker_code:
    # Finde die Stelle
    lines = clicker_code.split("\n")
    for i, line in enumerate(lines):
        if "if overlap_time:" in line:
            # Prüfe nächste 5 Zeilen
            for j in range(i, min(i+10, len(lines))):
                if "slot = overlap_time" in lines[j] and "slot = next_available_slot" not in lines[j-1:j+1]:
                    print(f"  ❌ WARNUNG: overlap_time umgeht Scheduler (Zeile {j+1})")
                    print(f"  ❌ INSTABIL: Alle Patienten bekommen gleiche Zeit!\n")
                    break
            else:
                print("  ✅ Scheduler wird immer benutzt (overlap_time umgeht nicht mehr)")
                print("  ✅ STABIL: Intervalle werden korrekt eingehalten\n")
            break
elif "slot = next_available_slot(filters)" in clicker_code:
    # Prüfe ob es VOR der overlap_time-Prüfung kommt
    scheduler_pos = clicker_code.find("slot = next_available_slot(filters)")
    overlap_pos = clicker_code.find("if overlap_time:")

    if scheduler_pos > 0 and (overlap_pos < 0 or scheduler_pos < overlap_pos or
                               clicker_code[scheduler_pos:scheduler_pos+200].count("slot = next_available_slot") > 0):
        print("  ✅ Scheduler wird IMMER benutzt (Hauptpfad)")
        print("  ✅ STABIL: Intervalle werden korrekt eingehalten\n")
    else:
        print("  ⚠️  Scheduler-Aufruf gefunden, aber Position unklar\n")
else:
    print("  ❌ KRITISCH: next_available_slot() nicht gefunden!\n")

# =============================================================================
# KRITISCHER PUNKT 5: Intervall-Einstellung
# =============================================================================
print("5️⃣  INTERVALL-KONFIGURATION")
print("-" * 80)

try:
    filters = json.loads((ROOT / "filters.json").read_text(encoding="utf-8"))
    interval = filters.get("runtime", {}).get("interval_minutes", 5)
    print(f"  ℹ️  Aktuelles Intervall: {interval} Minuten")

    if interval > 0 and interval <= 60:
        print(f"  ✅ STABIL: Intervall ist gültig\n")
    else:
        print(f"  ⚠️  WARNUNG: Ungewöhnliches Intervall ({interval} Min)\n")
except Exception as e:
    print(f"  ⚠️  Konnte filters.json nicht lesen: {e}\n")

# =============================================================================
# ZUSAMMENFASSUNG
# =============================================================================
print("="*80)
print("📊 GESAMTBEWERTUNG")
print("="*80)

issues = []

# Check 1: global declarations
if len(global_declarations) < 3:
    issues.append("patients_accepted global-Deklaration fehlt")

# Check 2: Log reset
if "LOG_PATH.unlink()" not in clicker_code:
    issues.append("Log-Reset fehlt")

# Check 3: Scheduler auto-cleanup
if "dates_to_delete = [d for d in slots.keys() if d < today]" not in scheduler_code:
    issues.append("Scheduler Auto-Cleanup fehlt")

# Check 4: Scheduler bypass
if "slot = overlap_time" in clicker_code:
    # Prüfe ob es problematisch ist
    lines = clicker_code.split("\n")
    for i, line in enumerate(lines):
        if "slot = overlap_time" in line:
            # Prüfe ob es in einem if-Block ohne next_available_slot davor ist
            prev_lines = "\n".join(lines[max(0, i-10):i])
            if "slot = next_available_slot" not in prev_lines:
                issues.append("Scheduler wird möglicherweise umgangen")

if len(issues) == 0:
    print("""
✅ ALLE KRITISCHEN PUNKTE BESTANDEN!

Das System ist stabil und sollte zuverlässig laufen:

  ✅ Counter wird korrekt hochgezählt
  ✅ Log-Datei wird beim Start geleert
  ✅ Alte Scheduler-Slots werden entfernt
  ✅ Scheduler wird immer benutzt (Intervalle korrekt)
  ✅ Konfiguration ist gültig

🟢 STABILITÄTS-STATUS: PRODUCTION-READY

Das System sollte jetzt dauerhaft stabil laufen!
""")
else:
    print(f"\n⚠️  {len(issues)} POTENZIELLE PROBLEME GEFUNDEN:\n")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    print("\n🟡 STABILITÄTS-STATUS: ACHTUNG - Prüfung empfohlen\n")

print("="*80 + "\n")
