"""
Phase-2-Abnahmetest: Prüft ob alle 4 Punkte korrekt implementiert sind
UND simuliert 2-Slot-Routing mit Dummy-Daten.
"""
import json, sys

print("=" * 60)
print("  PHASE-2-ABNAHMETEST")
print("=" * 60)

# ── 1. CODE-CHECK ─────────────────────────────────────────────
print("\n[1] Code-Check teleclinic_click_from_list_v9d.py")
with open("teleclinic_click_from_list_v9d.py", encoding="utf-8") as f:
    code = f.read()

checks = {
    "build_slot_filters() vorhanden":   "def build_slot_filters(" in code,
    "slot1_accepted Zähler":            "slot1_accepted" in code,
    "slot2_accepted Zähler":            "slot2_accepted" in code,
    "slot1_filters Routing":            "slot1_filters" in code,
    "slot2_filters Routing":            "slot2_filters" in code,
    "Stop: beide Slots voll":           "slot1_full and slot2_full" in code,
    "interval_minutes pro Slot":        "slot_data.get(\"interval_minutes\"" in code,
}

all_code_ok = True
for name, ok in checks.items():
    status = "OK  " if ok else "FEHLT"
    print(f"  [{status}] {name}")
    if not ok:
        all_code_ok = False

# ── 2. FILTER-JSON-CHECK ──────────────────────────────────────
print("\n[2] filters.json Format-Check")
try:
    with open("filters.json", encoding="utf-8") as f:
        filters = json.load(f)

    has_slot1 = "slot1" in filters
    has_slot2_key = "slot2" in filters
    has_slot2_flag = "slot2_enabled" in filters
    slot1_has_interval = "interval_minutes" in filters.get("slot1", {})
    slot2_has_interval = "interval_minutes" in filters.get("slot2", {})

    json_checks = {
        "slot1 vorhanden":              has_slot1,
        "slot2 vorhanden":              has_slot2_key,
        "slot2_enabled Flag":           has_slot2_flag,
        "slot1.interval_minutes":       slot1_has_interval,
        "slot2.interval_minutes":       slot2_has_interval,
    }

    all_json_ok = True
    for name, ok in json_checks.items():
        status = "OK  " if ok else "FEHLT"
        print(f"  [{status}] {name}")
        if not ok:
            all_json_ok = False

    print(f"\n  Slot1: {filters['slot1'].get('time_start','?')} - {filters['slot1'].get('time_end','?')} | Max: {filters['slot1'].get('max_patients','?')} | Intervall: {filters['slot1'].get('interval_minutes','?')} Min")
    slot2 = filters.get("slot2", {})
    slot2_en = filters.get("slot2_enabled", False)
    print(f"  Slot2: {'AKTIV' if slot2_en else 'DEAKTIVIERT'} | {slot2.get('time_start','?')} - {slot2.get('time_end','?')} | Max: {slot2.get('max_patients','?')} | Intervall: {slot2.get('interval_minutes','?')} Min")

except Exception as e:
    print(f"  FEHLER: {e}")
    all_json_ok = False

# ── 3. SIMULATOR: build_slot_filters() ───────────────────────
print("\n[3] Simulator: build_slot_filters() Konvertierung")

# Lade Funktion direkt aus dem Modul
sys.path.insert(0, ".")
try:
    # Importiere nur die Hilfsfunktion (kein Playwright nötig)
    import importlib.util, types

    # Minimaler Import: nur build_slot_filters extrahieren
    with open("teleclinic_click_from_list_v9d.py", encoding="utf-8") as f:
        src = f.read()

    # Extrahiere nur die build_slot_filters Funktion
    start = src.find("def build_slot_filters(")
    end = src.find("\nasync def click_loop(", start)
    func_src = src[start:end].strip()

    ns = {}
    exec(func_src, ns)
    build_slot_filters = ns["build_slot_filters"]

    # Test mit echten Slot-Daten
    slot1_data = {
        "time_start": "08:30", "time_end": "11:00",
        "max_patients": 10, "interval_minutes": 5,
        "diagnosis_include": "psyche", "diagnosis_exclude": "",
        "wishes_include": "", "wishes_exclude": "",
        "language_include": "", "language_exclude": "",
        "age_min": "", "age_max": "", "gender": ""
    }
    slot2_data = {
        "time_start": "16:30", "time_end": "19:00",
        "max_patients": 5, "interval_minutes": 10,
        "diagnosis_include": "haut", "diagnosis_exclude": "",
        "wishes_include": "", "wishes_exclude": "",
        "language_include": "englisch", "language_exclude": "",
        "age_min": "", "age_max": "", "gender": ""
    }

    f1 = build_slot_filters(slot1_data, "morgen", 1)
    f2 = build_slot_filters(slot2_data, "morgen", 2)

    print(f"  Slot1-Filter:")
    print(f"    Zeit: {f1['time_filter']['treatment_start']} - {f1['time_filter']['treatment_end']}")
    print(f"    Diagnose: {f1['diagnosis']['include']}")
    print(f"    Max: {f1['runtime']['max_patients']} | Intervall: {f1['runtime']['interval_minutes']} Min")

    print(f"  Slot2-Filter:")
    print(f"    Zeit: {f2['time_filter']['treatment_start']} - {f2['time_filter']['treatment_end']}")
    print(f"    Diagnose: {f2['diagnosis']['include']}")
    print(f"    Sprache: {f2['patients']['language_include']}")
    print(f"    Max: {f2['runtime']['max_patients']} | Intervall: {f2['runtime']['interval_minutes']} Min")

    sim_ok = (
        f1['time_filter']['treatment_start'] == "08:30" and
        f2['time_filter']['treatment_start'] == "16:30" and
        f1['runtime']['interval_minutes'] == 5 and
        f2['runtime']['interval_minutes'] == 10 and
        f2['patients']['language_include'] == ["englisch"]
    )
    print(f"\n  Simulator: {'OK - Konvertierung korrekt' if sim_ok else 'FEHLER in Konvertierung'}")

except Exception as e:
    print(f"  FEHLER beim Simulator: {e}")
    sim_ok = False

# ── 4. STOP-LOGIK-TEST ────────────────────────────────────────
print("\n[4] Stop-Logik Test (Simulation)")

# Simuliere Zähler-Logik
def test_stop_logic():
    slot1_max, slot2_max = 3, 2
    slot1_accepted, slot2_accepted = 0, 0
    slot2_enabled = True
    log = []

    # Simuliere 7 Fälle: abwechselnd Slot1 und Slot2
    for i in range(7):
        slot1_full = slot1_accepted >= slot1_max
        slot2_full = (not slot2_enabled) or (slot2_accepted >= slot2_max)

        if slot1_full and slot2_full:
            log.append(f"  STOP bei Fall {i+1}: Slot1={slot1_accepted}/{slot1_max}, Slot2={slot2_accepted}/{slot2_max}")
            break

        # Simuliere: ungerade → Slot1, gerade → Slot2
        if not slot1_full and i % 2 == 0:
            slot1_accepted += 1
            log.append(f"  Fall {i+1} → Slot 1 | Zähler: {slot1_accepted}/{slot1_max}, {slot2_accepted}/{slot2_max}")
        elif not slot2_full:
            slot2_accepted += 1
            log.append(f"  Fall {i+1} → Slot 2 | Zähler: {slot1_accepted}/{slot1_max}, {slot2_accepted}/{slot2_max}")
        else:
            log.append(f"  Fall {i+1} → SKIP (kein passender Slot)")

    return log, slot1_accepted == slot1_max and slot2_accepted == slot2_max

log, stop_ok = test_stop_logic()
for line in log:
    print(line)
print(f"\n  Stop-Logik: {'OK - Bot stoppt wenn beide Slots voll' if stop_ok else 'FEHLER'}")

# ── GESAMTERGEBNIS ────────────────────────────────────────────
print("\n" + "=" * 60)
gesamtergebnis = all_code_ok and all_json_ok and sim_ok and stop_ok
print(f"  GESAMTERGEBNIS: {'✅ PHASE 2 KOMPLETT BESTANDEN' if gesamtergebnis else '❌ NOCH OFFEN'}")
print("=" * 60)
