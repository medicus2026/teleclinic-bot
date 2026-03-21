#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug die Überschneidungs-Logik"""

from teleclinic_click_from_list_v9d import parse_time_range, calculate_overlap_start, time_to_minutes

# Test Fall aus dem Log:
# Patient: "22:00 - 00:00" (über Mitternacht)
# Sprechstunde: "11:00 - 13:00"

patient_text = "22:00 - 00:00"
patient_start, patient_end = parse_time_range(patient_text)
print(f"Patient: '{patient_text}'")
print(f"  → parsed: {patient_start} - {patient_end} min")
print(f"  → in HH:MM: {patient_start//60:02d}:{patient_start%60:02d} - {patient_end//60:02d}:{patient_end%60:02d}")

treatment_start_str = "11:00"
treatment_end_str = "13:00"
treatment_start = time_to_minutes(treatment_start_str)
treatment_end = time_to_minutes(treatment_end_str)
print(f"\nSprechstunde: '{treatment_start_str} - {treatment_end_str}'")
print(f"  → parsed: {treatment_start} - {treatment_end} min")

# Berechne Überschneidung
overlap = calculate_overlap_start(patient_start, patient_end, treatment_start, treatment_end)
print(f"\nÜberschneidung: {overlap}")

if overlap:
    print(f"❌ FEHLER: Sollte KEINE Überschneidung sein!")
else:
    print(f"✅ KORREKT: Keine Überschneidung")

# Jetzt Test mit korrektem Fall:
print("\n" + "="*60)
patient_text2 = "11:00 - 13:00"
patient_start2, patient_end2 = parse_time_range(patient_text2)
print(f"Patient: '{patient_text2}'")
print(f"  → parsed: {patient_start2} - {patient_end2} min")

overlap2 = calculate_overlap_start(patient_start2, patient_end2, treatment_start, treatment_end)
print(f"\nÜberschneidung: {overlap2}")

if overlap2:
    print(f"✅ KORREKT: Überschneidung vorhanden")
else:
    print(f"❌ FEHLER: Sollte Überschneidung sein!")
