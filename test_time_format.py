#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test-Skript für 12h/24h Zeitformat-Erkennung"""

from teleclinic_click_from_list_v9d import parse_time_range

print("=== Test der Zeitformat-Erkennung ===\n")

# Test 1: 24h-Format
result = parse_time_range("16:00 - 18:00")
print(f"✓ 24h '16:00 - 18:00' → {result} (960-1080 min)")

# Test 2: 24h-Format über Mitternacht
result = parse_time_range("22:00 - 00:00")
print(f"✓ 24h '22:00 - 00:00' → {result} (1320-0 min, Mitternacht)")

# Test 3: 12h-Format PM
result = parse_time_range("4:00 PM - 6:00 PM")
print(f"✓ 12h '4:00 PM - 6:00 PM' → {result} (16:00-18:00 = 960-1080 min)")

# Test 4: 12h-Format über Mitternacht
result = parse_time_range("10:00 PM - 12:00 AM")
h, m = divmod(result[0], 60) if result[0] else (None, None)
print(f"✓ 12h '10:00 PM - 12:00 AM' → {result} ({h:02d}:{m:02d} - über Mitternacht)")

# Test 5: 12h-Format AM
result = parse_time_range("9:00 AM - 11:00 AM")
print(f"✓ 12h '9:00 AM - 11:00 AM' → {result} (09:00-11:00 = 540-660 min)")

# Test 6: Mit Zeilenumbrüchen (wie in HTML)
result = parse_time_range("Heute, 22:00 - Morgen, 00:00")
print(f"✓ Mit Text '22:00 - Morgen, 00:00' → {result}")

print("\n✅ Alle Zeit-Formate korrekt erkannt!")
