# 🛠️ Plan: GUI-Erweiterung — 2. Zeitslot mit eigenen Filtern

**Erstellt:** 2026-03-22  
**Status:** Planung  
**Ziel:** Optionaler 2. Zeitslot mit komplett separaten Filtern (Diagnose, Wünsche, Sprache, Alter, Geschlecht, Max-Patienten)

---

## 1. Übersicht: Was soll passieren?

| Feature | Beschreibung |
|---------|-------------|
| **Checkbox** | „Erweiterten 2. Slot aktivieren" in GUI |
| **Aufklappbereich** | Unter Slot 1 erscheint ein kompletter 2. Filterblock |
| **Separate Filter je Slot** | Diagnose, Wünsche, Sprache, Alter, Geschlecht, Max-Patienten — alles pro Slot einzeln |
| **Ein Bot-Loop** | Keine zweite Engine, kein zweiter Browser — gleicher Scan-Flow |
| **Slot-Routing** | Jeder gefundene Fall wird gegen Slot-1-Filter UND Slot-2-Filter geprüft |
| **Pro-Slot-Limit** | `max_patients` gilt pro Slot (z. B. Slot 1 = 30, Slot 2 = 5) |
| **Abwärtskompatibel** | Wenn Slot 2 deaktiviert: Verhalten exakt wie bisher |

### Beispiel-Szenario (dein Wunsch)

| | Slot 1 (Vormittag) | Slot 2 (Nachmittag) |
|-|---------------------|---------------------|
| **Zeit** | 08:30 – 11:00 | 14:00 – 18:00 |
| **Sprache** | kein Englisch | nur Englisch |
| **Diagnose** | nur AU | nur Psyche |
| **Max Patienten** | 30 | 5 |

---

## 2. Betroffene Dateien

| Datei | Änderungsart | Risiko |
|-------|-------------|--------|
| `tc_main_gui.py` | GUI-Layout: Checkbox + aufklappbarer Slot-2-Block | Mittel |
| `filters.json` | Neues Datenmodell (slot1/slot2) | Niedrig |
| `teleclinic_click_from_list_v9d.py` | Slot-Routing + pro-Slot-Counter + pro-Slot-Filter | Mittel |
| `core_scheduler.py` | Pro-Slot-Zählung (bereits vorbereitet) | Niedrig (schon gemacht) |
| `scheduled_patients.py` | Optional: Slot-Name pro Patient speichern | Niedrig |

---

## 3. Neues Datenmodell: `filters.json`

### Aktuell (flach, ein Satz Filter):
```json
{
  "time_filter": { "treatment_start": "08:30", "treatment_end": "11:00", "treatment_start_2": "16:30", "treatment_end_2": "19:00" },
  "runtime": { "max_patients": 10, "interval_minutes": 5 },
  "patients": { "gender": "", "language_include": [], "language_exclude": [] },
  "diagnosis": { "include": "psyche", "exclude": "" },
  "wishes": { "include": "", "exclude": "" },
  "loop": { "scan_interval_sec": 5, "max_pages": 5 }
}
```

### Neu (pro Slot, abwärtskompatibel):
```json
{
  "time_filter": {
    "day_window": "morgen"
  },
  "slot1": {
    "time_start": "08:30",
    "time_end": "11:00",
    "max_patients": 30,
    "diagnosis_include": "",
    "diagnosis_exclude": "",
    "wishes_include": "AU",
    "wishes_exclude": "",
    "language_include": "",
    "language_exclude": "englisch",
    "age_min": "",
    "age_max": "",
    "gender": ""
  },
  "slot2_enabled": false,
  "slot2": {
    "time_start": "14:00",
    "time_end": "18:00",
    "max_patients": 5,
    "diagnosis_include": "psyche",
    "diagnosis_exclude": "",
    "wishes_include": "",
    "wishes_exclude": "",
    "language_include": "englisch",
    "language_exclude": "",
    "age_min": "",
    "age_max": "",
    "gender": ""
  },
  "runtime": {
    "interval_minutes": 5,
    "headless": false,
    "slowmo_ms": 0
  },
  "loop": {
    "scan_interval_sec": 5,
    "max_pages": 5
  }
}
```

### Migration alter `filters.json`:
- Beim Laden prüfen: Gibt es `slot1`? → neues Format.
- Gibt es nur `time_filter` + `diagnosis` + `patients`? → altes Format → automatisch in `slot1` konvertieren, `slot2_enabled = false`.
- **Kein Datenverlust**, kein manueller Eingriff nötig.

---

## 4. GUI-Layout-Plan (`tc_main_gui.py`)

### Aktuell (Zeilen im Filter-Frame):
```
Zeile 0:  Tag           [heute/morgen/später]
Zeile 1:  Zeit von      [08:30]     bis     [11:00]
Zeile 2:  Zeit von 2    [16:30]     bis 2   [19:00]       ← existiert schon, aber ohne eigene Filter
Zeile 3:  Alter min     []          max     []
Zeile 4:  Geschlecht    [egal]
Zeile 5:  Diagnose      []
Zeile 6:  Wünsche       []
Zeile 7:  Sprache       []
Zeile 8:  Diagnose ausschließen []
Zeile 9:  Wünsche ausschließen  []
Zeile 10: Sprache ausschließen  []
Zeile 11: Max Patienten [5]
Zeile 12: Scan-Intervall / Behandlungsintervall
Zeile 13: Max Seiten
```

### Neu:
```
━━━ SLOT 1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Zeile 0:  Tag           [heute/morgen/später]     ← global (gilt für beide)
Zeile 1:  Zeit von      [08:30]     bis     [11:00]
Zeile 2:  Diagnose      []
Zeile 3:  Wünsche       []
Zeile 4:  Sprache       []
Zeile 5:  Diagnose ausschl. []
Zeile 6:  Wünsche ausschl.  []
Zeile 7:  Sprache ausschl.  []
Zeile 8:  Alter min []  max []   Geschlecht [egal]
Zeile 9:  Max Patienten [30]

━━━ ☐ 2. Zeitslot aktivieren ━━━━━━━━━  ← Checkbox
Zeile 10: Zeit von      [14:00]     bis     [18:00]
Zeile 11: Diagnose      [psyche]
Zeile 12: Wünsche       []
Zeile 13: Sprache       [englisch]
Zeile 14: Diagnose ausschl. []
Zeile 15: Wünsche ausschl.  []
Zeile 16: Sprache ausschl.  []
Zeile 17: Alter min []  max []   Geschlecht [egal]
Zeile 18: Max Patienten [5]

━━━ ALLGEMEIN ━━━━━━━━━━━━━━━━━━━━━━━━━
Zeile 19: Scan-Intervall [5 s]  Behandlungsintervall [5 min]
Zeile 20: Max Seiten [5]
```

### GUI-Verhalten bei Checkbox:
- **Checkbox AUS**: Slot-2-Block ist ausgegraut/versteckt (`grid_remove()`). Nur Slot 1 aktiv.
- **Checkbox AN**: Slot-2-Block erscheint. Beide Slots aktiv.
- Slot-2-Felder werden beim Ausblenden NICHT gelöscht — beim erneuten Einblenden stehen die alten Werte noch da.

---

## 5. Slot-Routing im Bot (`teleclinic_click_from_list_v9d.py`)

### Aktuelle Logik (vereinfacht):
```
Für jeden Fall auf der Seite:
  1. check_case_matches_filters(fall, filters)  → passt oder nicht
  2. Falls passt: handle_case() → klick + Termin setzen
  3. patients_accepted++ (global)
  4. if patients_accepted >= max_patients → STOP
```

### Neue Logik:
```
Für jeden Fall auf der Seite:
  1. check_case_matches_slot(fall, slot1_filters) → passt zu Slot 1?
  2. check_case_matches_slot(fall, slot2_filters) → passt zu Slot 2? (nur wenn slot2_enabled)
  3. Ergebnis:
     - Passt nur zu Slot 1 → übernehme in Slot 1 (falls Slot-1-Limit nicht erreicht)
     - Passt nur zu Slot 2 → übernehme in Slot 2 (falls Slot-2-Limit nicht erreicht)
     - Passt zu beiden → nimm Slot mit niedrigerem Füllstand (oder Slot 1 als Default)
     - Passt zu keinem → skip
  4. slot1_accepted++ oder slot2_accepted++
  5. if slot1_accepted >= slot1_max UND slot2_accepted >= slot2_max → STOP
  6. Log: "Slot 1: 12/30 | Slot 2: 3/5"
```

### Wichtig — was NICHT geändert wird:
- `handle_case()` bleibt identisch (klickt + setzt Zeit)
- `start_chrome_debug_mode()` bleibt identisch
- `ensure_teleclinic_requests_page()` bleibt identisch
- `parse_time_range()` bleibt identisch
- `normalize_term()` / Synonym-Dicts bleiben identisch
- Playwright-Connection bleibt identisch

### Was angepasst wird:
| Funktion | Änderung |
|----------|---------|
| `load_filters()` | Neues Format laden + Migration |
| `check_case_matches_filters()` | Wird zu `check_case_matches_slot()` — bekommt Slot-spezifische Filter |
| `click_loop()` | Zwei Zähler (`slot1_accepted`, `slot2_accepted`), Slot-Routing, neue Stop-Bedingung |
| `main()` | Slots-Reset für beide Slots |

---

## 6. Umsetzungsschritte (Reihenfolge)

### Schritt 1: `filters.json` — Neues Format + Migration
- Neues Datenmodell definieren (wie oben)
- Migrationsfunktion schreiben: `migrate_filters(data) → new_data`
- In `load_filters()` einbauen

### Schritt 2: `tc_main_gui.py` — Slot-1-Block umbenennen
- Bestehende Felder in einen `slot1_frame` gruppieren
- Label anpassen ("Slot 1 — Vormittag" o.ä.)

### Schritt 3: `tc_main_gui.py` — Checkbox + Slot-2-Block
- `self.slot2_enabled = tk.BooleanVar(value=False)`
- Checkbox erstellen
- `slot2_frame` mit allen Feldern (Kopie von Slot 1)
- `toggle_slot2()` → `grid()` / `grid_remove()`
- `save_filters()` anpassen: schreibt neues Format
- `load_filters()` anpassen: liest neues Format + Migration

### Schritt 4: `teleclinic_click_from_list_v9d.py` — Hilfsfunktion für Slot-Filter
- `build_slot_filters(slot_data)` → erzeugt ein Filter-Dict im alten Format aus Slot-Daten
- Damit kann `check_case_matches_filters()` **unverändert** wiederverwendet werden!

### Schritt 5: `teleclinic_click_from_list_v9d.py` — Slot-Routing in `click_loop()`
- Zwei Zähler: `slot1_accepted`, `slot2_accepted`
- Zwei Limits: `slot1_max`, `slot2_max`
- Für jeden Fall: prüfe gegen Slot 1, dann Slot 2
- Übergib den passenden Slot-Filter an `handle_case()`
- Neue Stop-Bedingung: beide Slots voll

### Schritt 6: `core_scheduler.py` — Pro-Slot-Begrenzung (bereits vorbereitet ✅)
- `next_available_slot()` unterstützt bereits zwei Zeitfenster
- `validate_max_patients()` zählt bereits pro Slot

### Schritt 7: Test
- Nur Slot 1 aktiv → Verhalten wie bisher
- Slot 2 aktiviert → separate Filter greifen
- Slot 1 voll, Slot 2 noch offen → Bot läuft weiter
- Beide voll → Bot stoppt

### Schritt 8: Git-Commit + Backup
- Commit: `"feat: GUI Slot 2 mit separaten Filtern"`
- Tag: `v2.1.0-slot2`

---

## 7. Risiken + Gegenmaßnahmen

| Risiko | Wahrscheinlichkeit | Gegenmaßnahme |
|--------|-------------------|---------------|
| Migration löscht alte Filter | Niedrig | Fallback auf Defaults + Backup vor Migration |
| GUI wird zu lang/unübersichtlich | Mittel | Slot-2-Block per Checkbox ein-/ausblendbar |
| Bot wird langsamer durch doppelte Filterprüfung | Sehr niedrig | Filter-Check ist reine String-Vergleiche (< 1ms) |
| Slot 1 und Slot 2 überlappen zeitlich | Mittel | Warnung in GUI, wenn Zeiten sich überschneiden |
| Alte `filters.json` wird nicht erkannt | Niedrig | Explizite Versionserkennung (`"format_version": 2`) |

---

## 8. Was STABIL bleibt (nicht anfassen!)

- ✅ Playwright-Connection + Chrome-Debug-Modus
- ✅ `handle_case()` (Klick + Terminsetzen)
- ✅ `parse_time_range()` + `calculate_overlap_start()`
- ✅ `normalize_term()` + alle Synonym-Dicts
- ✅ `ensure_teleclinic_requests_page()` (Navigation)
- ✅ `validate_and_fix_day_filter()` (Tagesfilter)
- ✅ Overnight-Scanning / Mitternacht-Check
- ✅ Lizenz-System
- ✅ Terminkalender-Anzeige (nur Datenquelle erweitern)

---

## 9. Geschätzter Aufwand

| Schritt | Aufwand |
|---------|---------|
| Datenmodell + Migration | ~30 Min |
| GUI Slot-2-Block | ~45 Min |
| Slot-Routing im Bot | ~45 Min |
| Tests + Feinschliff | ~30 Min |
| **Gesamt** | **~2,5 Stunden** |

---

## 10. Nächster Schritt

> **Empfehlung:** Schritt 1 + 2 + 3 zusammen umsetzen (GUI fertig), dann Schritt 4 + 5 (Bot-Logik), dann Schritt 7 (Test).
>
> Soll ich jetzt mit Schritt 1 (Datenmodell + Migration) beginnen?
