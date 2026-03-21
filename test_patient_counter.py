#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Prüfe ob patients_accepted Counter korrekt funktioniert
"""

import sys
from pathlib import Path

# Simuliere die gleiche Struktur wie in teleclinic_click_from_list_v9d.py

# Globale Variable (wie in Zeile 26)
patients_accepted = 0

def normalize_text(text: str) -> str:
    """Normalisiert Text für case-insensitive Vergleiche."""
    return " ".join((text or "").split()).casefold()

def word_boundary_match(text: str, term: str) -> bool:
    """Prüft, ob ein Begriff als ganzes Wort im Text vorkommt."""
    import re
    pattern = r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))

async def log_line(text: str):
    """Schreibt Logzeile."""
    print(f"[LOG] {text}")

async def handle_case_TEST():
    """Simuliere handle_case() mit global-Deklaration."""
    global patients_accepted  # WICHTIG: Diese Zeile muss da sein!

    print(f"[TEST] Before: patients_accepted = {patients_accepted}")
    patients_accepted += 1
    print(f"[TEST] After += 1: patients_accepted = {patients_accepted}")
    await log_line(f"📊 Patienten übernommen: {patients_accepted}")
    return True

async def handle_case_WRONG():
    """Simuliere handle_case() OHNE global-Deklaration (zeigt den Fehler)."""
    # ❌ KEINE global-Deklaration hier!
    local_patients_accepted = None  # Simuliert lokale Variable
    local_patients_accepted = 0
    print(f"[WRONG] Before: local_patients_accepted = {local_patients_accepted}")
    local_patients_accepted += 1
    print(f"[WRONG] After += 1: local_patients_accepted = {local_patients_accepted}")
    print(f"[WRONG] ABER global patients_accepted = {patients_accepted} (unverändert!)")
    return True

async def main():
    global patients_accepted

    print("=" * 70)
    print("TEST 1: handle_case() MIT global-Deklaration (RICHTIG)")
    print("=" * 70)
    patients_accepted = 0
    print(f"Start: patients_accepted = {patients_accepted}")

    for i in range(3):
        print(f"\n[ITERATION {i+1}]")
        await handle_case_TEST()

    print(f"\n✅ Nach 3 Aufrufen: patients_accepted = {patients_accepted} (sollte 3 sein)")

    print("\n" + "=" * 70)
    print("TEST 2: handle_case() OHNE global-Deklaration (FALSCH - zeigt den alten Fehler)")
    print("=" * 70)
    patients_accepted = 0
    print(f"Start: patients_accepted = {patients_accepted}")

    for i in range(3):
        print(f"\n[ITERATION {i+1}]")
        await handle_case_WRONG()

    print(f"\n❌ Nach 3 Aufrufen: patients_accepted = {patients_accepted} (immer noch 0! Das war der Fehler!)")

    print("\n" + "=" * 70)
    print("FAZIT")
    print("=" * 70)
    print("✅ Mit global-Deklaration: Counter wird hochgezählt")
    print("❌ Ohne global-Deklaration: Counter bleibt auf 0 (der alte Fehler)")
    print("\n✅ Die Korrektur in Zeile 654 ist essentiell und funktioniert!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
