#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Scheduler-Intervalle korrekt?
"""

import json
from pathlib import Path
from core_scheduler import next_available_slot, reset_slots_for_date

ROOT = Path(__file__).resolve().parent
FILTER_PATH = ROOT / "filters.json"

# Lade aktuelle Filter
filters = json.loads(FILTER_PATH.read_text(encoding="utf-8"))

print("\n" + "="*80)
print("TEST: Scheduler vergibt Slots mit korrektem Intervall")
print("="*80)

# Reset Slots
reset_slots_for_date()
print("\n✅ Slots zurückgesetzt\n")

# Zeige Config
tf = filters.get("time_filter", {})
rt = filters.get("runtime", {})
start = tf.get("treatment_start", "08:00")
end = tf.get("treatment_end", "18:00")
interval = rt.get("interval_minutes", 5)

print(f"Konfiguration aus filters.json:")
print(f"  Start: {start}")
print(f"  Ende: {end}")
print(f"  Intervall: {interval} Minuten")
print(f"\n{'='*80}\n")

# Vergebe 5 Slots
print("Vergebe 5 Test-Slots:\n")
slots = []
for i in range(5):
    slot = next_available_slot(filters)
    if slot:
        slots.append(slot)
        print(f"  Slot {i+1}: {slot}")
    else:
        print(f"  Slot {i+1}: FEHLER - kein Slot verfügbar!")
        break

# Prüfe Intervalle
print(f"\n{'='*80}")
print("INTERVALL-PRÜFUNG:")
print("="*80 + "\n")

if len(slots) >= 2:
    for i in range(len(slots)-1):
        h1, m1 = map(int, slots[i].split(":"))
        h2, m2 = map(int, slots[i+1].split(":"))
        diff = (h2*60 + m2) - (h1*60 + m1)

        if diff == interval:
            print(f"  ✅ {slots[i]} → {slots[i+1]} = {diff} Min (korrekt)")
        else:
            print(f"  ❌ {slots[i]} → {slots[i+1]} = {diff} Min (erwartet: {interval} Min)")

print("\n" + "="*80)
if all((int(slots[i+1].split(":")[0])*60 + int(slots[i+1].split(":")[1])) -
       (int(slots[i].split(":")[0])*60 + int(slots[i].split(":")[1])) == interval
       for i in range(len(slots)-1)):
    print("✅ TEST BESTANDEN - Alle Intervalle korrekt!")
else:
    print("❌ TEST FEHLGESCHLAGEN - Intervalle nicht korrekt!")
print("="*80 + "\n")
