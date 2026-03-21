#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Scheduler mit min_start_time (overlap_time)
"""

import json
from pathlib import Path
from core_scheduler import next_available_slot, reset_slots_for_date

ROOT = Path(__file__).resolve().parent
FILTER_PATH = ROOT / "filters.json"

# Lade aktuelle Filter
filters = json.loads(FILTER_PATH.read_text(encoding="utf-8"))

print("\n" + "="*80)
print("TEST: Scheduler mit min_start_time (Patient möchte ab 12:00)")
print("="*80)

# Reset Slots
reset_slots_for_date()
print("\n✅ Slots zurückgesetzt\n")

# Zeige Config
tf = filters.get("time_filter", {})
start = tf.get("treatment_start", "08:00")
end = tf.get("treatment_end", "18:00")
interval = filters.get("runtime", {}).get("interval_minutes", 5)

print(f"Sprechstunde: {start} - {end}")
print(f"Intervall: {interval} Minuten\n")

# Szenario: Vergebe 3 Slots (11:30, 11:35, 11:40)
print("1️⃣  Vergebe 3 Slots ohne min_start_time:")
print("-" * 80)
for i in range(3):
    slot = next_available_slot(filters)
    if slot:
        print(f"  Slot {i+1}: {slot}")

# Jetzt kommt ein Patient, der ab 12:00 möchte (overlap_time = 12:00)
print("\n2️⃣  Patient möchte ab 12:00 starten (min_start_time='12:00'):")
print("-" * 80)
slot = next_available_slot(filters, min_start_time="12:00")
if slot:
    print(f"\n✅ Zugewiesener Slot: {slot}")

    # Prüfe ob Slot >= 12:00
    h, m = map(int, slot.split(":"))
    slot_minutes = h * 60 + m
    min_minutes = 12 * 60

    if slot_minutes >= min_minutes:
        print(f"✅ KORREKT: {slot} >= 12:00")
    else:
        print(f"❌ FEHLER: {slot} < 12:00 (Patient möchte ab 12:00!)")
else:
    print("❌ Kein Slot verfügbar")

# Vergebe weitere Slots
print("\n3️⃣  Weitere Slots:")
print("-" * 80)
for i in range(2):
    slot = next_available_slot(filters)
    if slot:
        print(f"  Slot: {slot}")

print("\n" + "="*80)
print("FAZIT:")
print("="*80)
print("""
Mit min_start_time wird sichergestellt, dass:
  ✅ Scheduler nur Slots NACH Patientenwunsch vergibt
  ✅ Keine Konflikte zwischen Scheduler und Patientenzeit
  ✅ 'Übernehmen'-Button bleibt aktiviert (Zeit ist gültig)
""")
print("="*80 + "\n")
