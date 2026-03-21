#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test der Scheduler-Validierung"""

from core_scheduler import validate_max_patients, calculate_max_slots, hhmm_to_minutes
import json

filters = json.load(open('filters.json'))

print("\n" + "="*70)
print("TEST: validate_max_patients()")
print("="*70)

requested, possible, valid = validate_max_patients(filters)
print(f"\nErgebnis:")
print(f"  Wunsch: {requested}")
print(f"  Möglich: {possible}")
print(f"  Erreichbar: {valid}")

# Manueller Test
tf = filters.get("time_filter", {})
rt = filters.get("runtime", {})

start = hhmm_to_minutes(tf.get("treatment_start", "08:00"))
end = hhmm_to_minutes(tf.get("treatment_end", "18:00"))
interval = int(rt.get("interval_minutes", 5))

print(f"\nZeitintervall:")
print(f"  Start: {start} min ({start//60:02d}:{start%60:02d})")
print(f"  Ende:  {end} min ({end//60:02d}:{end%60:02d})")
print(f"  Intervall: {interval} min")
print(f"  Verfügbar: {end-start} Minuten")

max_slots = calculate_max_slots(start, end, interval)
print(f"  Max Slots: {max_slots}")

print("\n" + "="*70)
