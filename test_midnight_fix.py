"""
Test: Über-Mitternacht-Fix für parse_time_range und minutes_to_hhmm
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("  TEST: ÜBER-MITTERNACHT-FIX")
print("=" * 60)

# --- parse_time_range ---
from teleclinic_click_from_list_v9d import parse_time_range

print("\n[1] parse_time_range Tests")
tests = [
    ("22:00 - 00:00",  1320, 1440, "Über-Mitternacht"),
    ("23:00 - 01:00",  1380, 1500, "Über-Mitternacht (01:00)"),
    ("20:00 - 22:00",  1200, 1320, "Normal"),
    ("08:00 - 10:00",   480,  600, "Normal Morgen"),
    ("00:00 - 02:00",     0,  120, "Ab Mitternacht"),
]
all_ok = True
for text, exp_s, exp_e, label in tests:
    s, e = parse_time_range(text)
    ok = (s == exp_s and e == exp_e)
    print(f"  {'OK  ' if ok else 'FAIL'} {label:30s} '{text}' → {s}-{e} (erwartet {exp_s}-{exp_e})")
    if not ok:
        all_ok = False

# --- calculate_overlap_start ---
from teleclinic_click_from_list_v9d import calculate_overlap_start

print("\n[2] Überschneidungs-Tests")
overlap_tests = [
    # patient_start, patient_end, treatment_start, treatment_end, expected
    (1320, 1440, 1380, 1410, "23:00"),   # 22:00-00:00 vs Slot 23:00-23:30
    (1320, 1440, 1320, 1380, "22:00"),   # 22:00-00:00 vs Slot 22:00-23:00
    (1200, 1320, 1380, 1410,  None),     # 20:00-22:00 vs Slot 23:00-23:30 → kein Match
    ( 480,  600,  540,  660, "09:00"),   # 08:00-10:00 vs Slot 09:00-11:00
]
for ps, pe, ts, te, exp in overlap_tests:
    result = calculate_overlap_start(ps, pe, ts, te)
    ok = (result == exp)
    print(f"  {'OK  ' if ok else 'FAIL'} Patient {ps//60:02d}:{ps%60:02d}-{pe%1440//60:02d}:{pe%60:02d} "
          f"vs Slot {ts//60:02d}:{ts%60:02d}-{te//60:02d}:{te%60:02d} "
          f"→ {result} (erwartet {exp})")
    if not ok:
        all_ok = False

# --- minutes_to_hhmm ---
from core_scheduler import minutes_to_hhmm

print("\n[3] minutes_to_hhmm Tests")
hhmm_tests = [
    (1380, "23:00"),
    (1440, "00:00"),  # Mitternacht
    (1500, "01:00"),  # 01:00 nächster Tag
    ( 600, "10:00"),
    (   0, "00:00"),
]
for m, exp in hhmm_tests:
    r = minutes_to_hhmm(m)
    ok = (r == exp)
    print(f"  {'OK  ' if ok else 'FAIL'} {m:4d} Min → {r} (erwartet {exp})")
    if not ok:
        all_ok = False

print("\n" + "=" * 60)
print(f"  ERGEBNIS: {'✅ ALLE TESTS BESTANDEN' if all_ok else '❌ FEHLER GEFUNDEN'}")
print("=" * 60)
