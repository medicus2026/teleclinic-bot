#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug parse_time_range für "22:00 - 00:00" Psychische Leiden"""

from teleclinic_click_from_list_v9d import parse_time_range

# Das ist der exakte Text aus dem Log
text = """22:00 - 00:00

GKV
VIDEO

Psychische Leiden

Weiblich, 30 Jahre, Rezept, weitere Informationen in de..."""

result = parse_time_range(text)
print(f"Input: (multiline text mit '22:00 - 00:00')")
print(f"Result: {result}")

if result:
    start, end = result
    print(f"  Start: {start//60:02d}:{start%60:02d} (min: {start})")
    print(f"  End:   {end//60:02d}:{end%60:02d} (min: {end})")
else:
    print("  Result: None")

# Test auch einzeln
print("\n" + "="*60)
result2 = parse_time_range("22:00 - 00:00")
print(f"Input: '22:00 - 00:00'")
print(f"Result: {result2}")

if result2:
    start, end = result2
    print(f"  Start: {start//60:02d}:{start%60:02d} (min: {start})")
    print(f"  End:   {end//60:02d}:{end%60:02d} (min: {end})")
else:
    print("  Result: None")
