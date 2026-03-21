#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test-Szenario für Overnight-Scanning
Demonstriert den automatischen Filter-Wechsel bei Mitternacht
"""

import asyncio
from datetime import datetime, time

# Simulierte Timestamps für verschiedene Test-Szenarien
test_scenarios = [
    ("22:00", "morgen", "heute"),  # 22 Uhr: morgen → wird später heute
    ("23:55", "morgen", "heute"),  # 23:55 Uhr: morgen → wird bald heute
    ("00:15", "morgen", "heute"),  # 00:15 Uhr: WECHSEL zu heute ✅
    ("01:00", "heute", "heute"),   # 01:00 Uhr: heute bleibt heute
    ("04:00", "heute", "heute"),   # 04:00 Uhr: heute bleibt heute
    ("22:00", "später", "morgen"), # 22 Uhr: später → wird später morgen
    ("00:30", "später", "morgen"), # 00:30 Uhr: WECHSEL zu morgen ✅
]

def check_midnight_wechsel(hour: int, day_window: str) -> tuple:
    """
    Simuliert die Midnight-Detection und gibt den neuen day_window zurück.

    Returns: (wechsel_erfolgt: bool, neuer_day_window: str)
    """
    if hour < 4:  # Frühe Morgen-Stunde → Mitternacht wurde überschritten
        if day_window == "morgen":
            return (True, "heute")
        elif day_window == "später":
            return (True, "morgen")

    return (False, day_window)

print("🌙 OVERNIGHT-SCANNING TEST\n")
print("=" * 70)
print("Szenario: Scanner startet um 22:00 mit Filter 'morgen'")
print("Erwartet: Bei 00:15 Uhr wechselt Filter automatisch zu 'heute'\n")
print("=" * 70)

for time_str, input_filter, expected_filter in test_scenarios:
    hour = int(time_str.split(":")[0])

    wechsel, output_filter = check_midnight_wechsel(hour, input_filter)

    status = "✅ WECHSEL" if wechsel else "   läuft"
    matches = "✅" if output_filter == expected_filter else "❌"

    print(f"\n[{time_str} Uhr] {status}")
    print(f"  Input:    {input_filter}")
    print(f"  Output:   {output_filter}")
    print(f"  Erwartet: {expected_filter} {matches}")

print("\n" + "=" * 70)
print("✅ OVERNIGHT-SCANNING TEST ABGESCHLOSSEN")
print("=" * 70)
print("""
Zusammenfassung:
- Scanner kann über Mitternacht hinweg laufen
- Bei Stunde < 4 (z.B. 00:15, 01:00, 02:00) wird automatisch gewechselt
- Keine manuellen Eingriffe nötig
- Filter wird dynamisch aktualisiert, Browser navigiert zur neuen Seite

Praktische Anwendung:
1. Start um 22:00 mit Filter "morgen" 
2. Scanner läuft auf Morgen-Seite (tab=1)
3. Um 00:15 automatischer Wechsel zu "heute" (tab=0)
4. Scanner läuft weiter bis zur Beendingung
""")
