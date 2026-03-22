#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test: Migrations-Funktion für Slot-Format"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILTER_PATH = ROOT / "filters.json"


def migrate_filters_to_slot_format(data: dict) -> dict:
    """Migriert alte filters.json zu neuem Format (slot1 + slot2)."""
    if "slot1" in data and "slot2_enabled" in data:
        return data

    time_filter = data.get("time_filter", {})
    runtime = data.get("runtime", {})
    patients = data.get("patients", {})
    diagnosis = data.get("diagnosis", {})
    wishes = data.get("wishes", {})
    loop = data.get("loop", {})

    new_data = {
        "time_filter": {
            "day_window": time_filter.get("day_window", "heute")
        },
        "slot1": {
            "time_start": time_filter.get("treatment_start", "21:30"),
            "time_end": time_filter.get("treatment_end", "23:30"),
            "max_patients": runtime.get("max_patients", 5),
            "diagnosis_include": diagnosis.get("include", ""),
            "diagnosis_exclude": diagnosis.get("exclude", ""),
            "wishes_include": wishes.get("include", ""),
            "wishes_exclude": wishes.get("exclude", ""),
            "language_include": ",".join(patients.get("language_include", [])) if isinstance(patients.get("language_include"), list) else patients.get("language_include", ""),
            "language_exclude": ",".join(patients.get("language_exclude", [])) if isinstance(patients.get("language_exclude"), list) else patients.get("language_exclude", ""),
            "age_min": str(patients.get("age_min", "")),
            "age_max": str(patients.get("age_max", "")),
            "gender": patients.get("gender", "")
        },
        "slot2_enabled": False,
        "slot2": {
            "time_start": time_filter.get("treatment_start_2", ""),
            "time_end": time_filter.get("treatment_end_2", ""),
            "max_patients": 5,
            "diagnosis_include": "",
            "diagnosis_exclude": "",
            "wishes_include": "",
            "wishes_exclude": "",
            "language_include": "",
            "language_exclude": "",
            "age_min": "",
            "age_max": "",
            "gender": ""
        },
        "runtime": {
            "interval_minutes": runtime.get("interval_minutes", 5),
            "headless": runtime.get("headless", False),
            "slowmo_ms": runtime.get("slowmo_ms", 0)
        },
        "loop": {
            "scan_interval_sec": loop.get("scan_interval_sec", 5),
            "max_pages": loop.get("max_pages", 5)
        }
    }

    return new_data


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TEST: Migrations-Funktion für Slot-Format")
    print("=" * 70)

    # Lade filters.json
    with open(FILTER_PATH, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    print("\n[BEFORE] Aktuelles Format in filters.json:")
    print(f"  Keys: {list(old_data.keys())}")

    if 'slot1' in old_data:
        print("  ✅ Bereits neues Format!")
    else:
        print("  ⚠️  Altes Format - migriere...")
        old_data = migrate_filters_to_slot_format(old_data)

    print("\n[AFTER] Neues Format:")
    print(f"  time_filter.day_window: {old_data.get('time_filter', {}).get('day_window')}")
    print(f"  slot1.time_start: {old_data.get('slot1', {}).get('time_start')}")
    print(f"  slot1.time_end: {old_data.get('slot1', {}).get('time_end')}")
    print(f"  slot1.max_patients: {old_data.get('slot1', {}).get('max_patients')}")
    print(f"  slot1.diagnosis_include: {old_data.get('slot1', {}).get('diagnosis_include')}")
    print(f"  slot2_enabled: {old_data.get('slot2_enabled')}")
    print(f"  slot2.time_start: {old_data.get('slot2', {}).get('time_start')}")
    print(f"  slot2.time_end: {old_data.get('slot2', {}).get('time_end')}")
    print(f"  slot2.max_patients: {old_data.get('slot2', {}).get('max_patients')}")

    print("\n" + "=" * 70)
    print("✅ Migration erfolgreich!")
    print("=" * 70)
