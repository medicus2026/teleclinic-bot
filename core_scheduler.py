from pathlib import Path
import json
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SLOTS_FILE = ROOT / "scheduled_slots.json"


def hhmm_to_minutes(hhmm: str) -> int:
    """Wandelt HH:MM in Minuten um."""
    try:
        h, m = map(int, hhmm.strip().split(":"))
        return h * 60 + m
    except Exception:
        return 0  # Standardwert im Fehlerfall


def minutes_to_hhmm(m: int) -> str:
    """Wandelt Minuten in HH:MM-Format um. Zeiten >= 1440 (nächster Tag) werden modulo 24h gerechnet."""
    m = m % (24 * 60)  # Über-Mitternacht: 1440 → 00:00, 1500 → 01:00
    return f"{m // 60:02d}:{m % 60:02d}"


def load_slots() -> dict:
    """Lädt gespeicherte Slots oder gibt leere Struktur zurück."""
    if not SLOTS_FILE.exists():
        return {}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(SLOTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                time.sleep(0.05)  # Kurz warten
                continue
            print(f"[SCHEDULER] Warnung: Konnte Slots nicht laden: {e}")
            return {}
        except json.JSONDecodeError:
            # Beschädigte Datei
            return {}
    return {}


def save_slots(slots: dict) -> None:
    """Schreibt aktualisierte Slots atomar."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Schreibe in Temp-Datei, dann atomar umbenennen
            tmp = SLOTS_FILE.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(slots, f, indent=2, ensure_ascii=False)
            tmp.replace(SLOTS_FILE)  # Atomic rename
            return
        except (IOError, OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                time.sleep(0.05)
                continue
            print(f"[SCHEDULER] Fehler beim Speichern: {e}")
            raise


def calculate_max_slots(start_min: int, end_min: int, interval: int) -> int:
    """
    Berechnet die maximale Anzahl Termine, die in einem Zeitraum möglich sind.

    Beispiel:
    - 19:00 bis 22:00 = 180 Minuten
    - Mit 5-Minuten-Intervall = 180/5 = 36 Slots (19:00, 19:05, 19:10, ...)
    """
    if start_min >= end_min or interval <= 0:
        return 0

    # Anzahl der 5-Minuten-Intervalle die in den Zeitraum passen
    available_minutes = end_min - start_min
    max_slots = available_minutes // interval
    return max_slots


def next_available_slot(filters: dict, date: str | None = None, min_start_time: str | None = None) -> str | None:
    """
    Gibt die nächste freie Zeit als HH:MM zurück.
    WICHTIG: Speichert den Slot NICHT sofort! Erst confirm_slot() aufrufen nach erfolgreichem Klick.

    Args:
        filters: Filter-Dict mit time_filter, runtime, etc.
        date: Datum (YYYY-MM-DD), default heute
        min_start_time: Früheste erlaubte Startzeit (HH:MM), z.B. bei overlap_time
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    slots = load_slots()
    today_slots = slots.get(date, [])

    # Debug-Info: Zeige bereits belegte Slots
    if today_slots:
        print(f"[SCHEDULER] Bereits belegte Slots für {date}: {', '.join(sorted(today_slots))}")
    else:
        print(f"[SCHEDULER] Keine Slots belegt für {date} - starte bei Behandlungsbeginn")

    tf = filters.get("time_filter", {})
    rt = filters.get("runtime", {})

    # Intervall mit Default 5 Minuten, falls nicht gesetzt
    interval = rt.get("interval_minutes", 5)
    try:
        interval = int(interval)
    except (ValueError, TypeError):
        interval = 5

    if interval <= 0:
        interval = 5
        print(f"[SCHEDULER] ⚠️ Ungültiges Intervall ({rt.get('interval_minutes')}), setze Default: 5 Minuten")

    direction = rt.get("fill_direction", "forward")

    # WICHTIG: Versuche BEIDE Zeitfenster (Slot 1 + Slot 2)
    time_ranges = []

    # Slot 1 (verpflichtend)
    t1_start = hhmm_to_minutes(tf.get("treatment_start", "08:00"))
    t1_end = hhmm_to_minutes(tf.get("treatment_end", "18:00"))
    if t1_start is not None and t1_end is not None and t1_start < t1_end:
        time_ranges.append((t1_start, t1_end, "Slot 1"))

    # Slot 2 (optional)
    t2_start_str = tf.get("treatment_start_2")
    t2_end_str = tf.get("treatment_end_2")
    t2_start = hhmm_to_minutes(t2_start_str) if t2_start_str else None
    t2_end = hhmm_to_minutes(t2_end_str) if t2_end_str else None
    if t2_start is not None and t2_end is not None and t2_start < t2_end:
        time_ranges.append((t2_start, t2_end, "Slot 2"))

    if not time_ranges:
        print("[ERROR] Keine gültigen Zeitfenster konfiguriert.")
        return None

    # Versuche in jedem Zeitfenster einen Slot zu finden
    for start, end, slot_name in time_ranges:
        # Passe Start an, falls min_start_time gesetzt
        actual_start = start
        if min_start_time:
            min_start_minutes = hhmm_to_minutes(min_start_time)
            if min_start_minutes > start:
                # FIX: Aufrunden auf nächstes gültiges Vielfaches des Intervalls ab start
                offset = min_start_minutes - start
                rounded_offset = ((offset + interval - 1) // interval) * interval
                actual_start = start + rounded_offset
                print(f"[SCHEDULER] Frühester Start angepasst auf: {minutes_to_hhmm(actual_start)} "
                      f"(Patientenwunsch ab {min_start_time}, auf Intervall-Raster ausgerichtet) in {slot_name}")

        print(f"[SCHEDULER] Durchsuche {slot_name}: {minutes_to_hhmm(actual_start)} - {minutes_to_hhmm(end)}, Intervall: {interval} Min.")

        if direction == "backward":
            current = end - interval
            while current >= actual_start:
                t = minutes_to_hhmm(current)
                if t not in today_slots:
                    # NUR FINDEN, NICHT SPEICHERN! confirm_slot() macht das später.
                    print(f"[SCHEDULER] 🔍 Slot {t} gefunden (rückwärts in {slot_name}). Noch nicht bestätigt.")
                    return t
                current -= interval
        else:
            # FORWARD: Beginne am Start und gehe vorwärts (9:00, 9:10, 9:20...)
            current = actual_start
            while current < end:
                t = minutes_to_hhmm(current)
                if t not in today_slots:
                    # NUR FINDEN, NICHT SPEICHERN! confirm_slot() macht das später.
                    print(f"[SCHEDULER] 🔍 Slot {t} gefunden (vorwärts in {slot_name}). Noch nicht bestätigt.")
                    return t
                else:
                    pass  # Slot bereits belegt, prüfe nächsten
                current += interval

    print("[WARN] Keine freien Slots mehr verfügbar in allen Zeitfenstern.")
    return None


def confirm_slot(slot_time: str, date: str | None = None) -> bool:
    """
    Bestätigt einen Slot als belegt NACH erfolgreichem Klick.
    Wird aufgerufen wenn handle_case() erfolgreich war.

    Returns: True wenn erfolgreich gespeichert
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    try:
        slots = load_slots()
        today_slots = slots.get(date, [])

        if slot_time not in today_slots:
            today_slots.append(slot_time)
            today_slots.sort()
            slots[date] = today_slots
            save_slots(slots)
            print(f"[SCHEDULER] ✅ Slot {slot_time} bestätigt und gespeichert für {date}. Gesamt belegt: {len(today_slots)}")
        else:
            print(f"[SCHEDULER] ℹ️ Slot {slot_time} war bereits belegt für {date}.")
        return True
    except Exception as e:
        print(f"[SCHEDULER] ❌ Fehler beim Bestätigen von Slot {slot_time}: {e}")
        return False


def validate_max_patients(filters: dict, existing_patients: dict) -> tuple[int, int, bool]:
    """
    Validiert die max_patients-Einstellung gegen die verfügbaren Slots.

    Bei 2 Zeitfenstern gilt max_patients pro Zeitfenster.

    Returns:
        (max_patients_requested, max_patients_possible_total, is_valid)
    """
    tf = filters.get("time_filter", {})
    rt = filters.get("runtime", {})

    # Lade Max-Patienten (pro Slot)
    max_patients_requested = rt.get("max_patients", 5)
    try:
        max_patients_requested = int(max_patients_requested)
    except (ValueError, TypeError):
        max_patients_requested = 5

    if max_patients_requested <= 0:
        max_patients_requested = 5

    interval = rt.get("interval_minutes", 5)
    try:
        interval = int(interval)
    except (ValueError, TypeError):
        interval = 5
    if interval <= 0:
        interval = 5

    # Ermittele verfügbare Slots je Zeitfenster
    ranges = []

    t1_start = hhmm_to_minutes(tf.get("treatment_start", "08:00"))
    t1_end = hhmm_to_minutes(tf.get("treatment_end", "18:00"))
    if t1_start is not None and t1_end is not None and t1_start < t1_end:
        ranges.append(("Slot 1", t1_start, t1_end))

    t2_start_str = tf.get("treatment_start_2")
    t2_end_str = tf.get("treatment_end_2")
    t2_start = hhmm_to_minutes(t2_start_str) if t2_start_str else None
    t2_end = hhmm_to_minutes(t2_end_str) if t2_end_str else None
    if t2_start is not None and t2_end is not None and t2_start < t2_end:
        ranges.append(("Slot 2", t2_start, t2_end))

    if not ranges:
        return (max_patients_requested, 0, False)

    per_slot_possible = []
    for slot_name, start, end in ranges:
        possible = calculate_max_slots(start, end, interval)
        # Berücksichtige bereits terminierte Patienten
        existing_count = sum(1 for time in existing_patients if start <= hhmm_to_minutes(time) < end)
        per_slot_possible.append((slot_name, start, end, possible - existing_count))

    # Gültig nur, wenn pro aktivem Slot der gewünschte Wert erreichbar ist
    is_valid = all(max_patients_requested <= possible for _, _, _, possible in per_slot_possible)

    max_patients_possible_total = sum(possible for _, _, _, possible in per_slot_possible)

    return (max_patients_requested, max_patients_possible_total, is_valid)


def reset_slots_for_date(date: str | None = None) -> None:
    """
    Löscht alle Slots für ein bestimmtes Datum.
    Zusätzlich: Löscht ALLE Slots die älter als heute sind (Cleanup).
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    slots = load_slots()

    # Hauptzweck: Lösche Slots für das gewünschte Datum
    if date in slots:
        del slots[date]

    # CLEANUP: Lösche auch alle Slots, die älter als heute sind
    today = datetime.now().strftime("%Y-%m-%d")
    dates_to_delete = [d for d in slots.keys() if d < today]

    for old_date in dates_to_delete:
        del slots[old_date]
        print(f"[SCHEDULER] 🧹 Alte Slots vom {old_date} gelöscht (älter als heute)")

    save_slots(slots)

    if date in dates_to_delete or date == today:
        print(f"[SCHEDULER] ✅ Alle Slots für {date} gelöscht.")


def show_scheduled_slots(date: str | None = None) -> None:
    """Zeigt alle belegten Slots für ein Datum an."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    slots = load_slots()
    today_slots = slots.get(date, [])

    if today_slots:
        print(f"\n[SCHEDULER] Belegte Slots für {date}:")
        print("=" * 50)
        for i, slot in enumerate(sorted(today_slots), 1):
            print(f"  {i}. {slot} Uhr")
        print("=" * 50)
        print(f"Gesamt: {len(today_slots)} Termine vergeben")
    else:
        print(f"[SCHEDULER] Keine Termine vergeben für {date}")


def reset_all_slots() -> None:
    """Löscht ALLE Slots (für neue Session)."""
    save_slots({})
    print("[SCHEDULER] ✅ Alle Slots komplett zurückgesetzt.")


def import_existing_appointments(appointments: list, date_heute: str | None = None, date_morgen: str | None = None) -> dict:
    """
    Überträgt aus Teleclinic gelesene Bestandstermine in scheduled_slots.json.
    Bestehende Einträge werden NICHT gelöscht — nur neue Slots hinzugefügt.

    Args:
        appointments: Liste von Dicts mit keys: time, diagnosis, day ("Heute"/"Morgen"), ...
        date_heute:   Datum für "Heute" als YYYY-MM-DD (default: heute)
        date_morgen:  Datum für "Morgen" als YYYY-MM-DD (default: morgen)

    Returns:
        Dict mit {"heute": [slots], "morgen": [slots], "neu_hinzugefuegt": int}
    """
    from datetime import timedelta

    if date_heute is None:
        date_heute = datetime.now().strftime("%Y-%m-%d")
    if date_morgen is None:
        date_morgen = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    slots = load_slots()
    neu_hinzugefuegt = 0

    for appt in appointments:
        time_str = appt.get("time", "").strip()
        day_label = appt.get("day", "Heute")

        if not time_str:
            continue

        # Datum bestimmen
        if day_label == "Morgen":
            date_key = date_morgen
        else:
            date_key = date_heute

        # Slot eintragen falls noch nicht vorhanden
        if date_key not in slots:
            slots[date_key] = []

        if time_str not in slots[date_key]:
            slots[date_key].append(time_str)
            slots[date_key].sort()
            neu_hinzugefuegt += 1
            print(f"[SCHEDULER] ✅ Bestandstermin importiert: {date_key} {time_str} ({appt.get('diagnosis','')})")
        else:
            print(f"[SCHEDULER] ℹ️  Slot bereits bekannt: {date_key} {time_str}")

    save_slots(slots)

    result = {
        "heute": slots.get(date_heute, []),
        "morgen": slots.get(date_morgen, []),
        "neu_hinzugefuegt": neu_hinzugefuegt,
        "date_heute": date_heute,
        "date_morgen": date_morgen,
    }
    print(f"[SCHEDULER] 📥 Import abgeschlossen: {neu_hinzugefuegt} neue Slots. "
          f"Heute={len(result['heute'])}, Morgen={len(result['morgen'])}")
    return result




if __name__ == "__main__":
    import sys

    cfg_path = ROOT / "filters.json"
    if not cfg_path.exists():
        print("[ERROR] filters.json nicht gefunden.")
        sys.exit(1)

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    # Zeige Menü
    print("\n" + "=" * 60)
    print("  SCHEDULER TEST & VERWALTUNG")
    print("=" * 60)
    print("1. Nächsten freien Slot anzeigen")
    print("2. Alle belegten Slots anzeigen")
    print("3. Slots für heute zurücksetzen")
    print("4. ALLE Slots zurücksetzen")
    print("5. 5 Test-Slots vergeben")
    print("=" * 60)

    choice = input("\nWählen Sie eine Option (1-5): ").strip()

    if choice == "1":
        slot = next_available_slot(cfg)
        if slot:
            print(f"\n✅ Nächster freier Slot: {slot}")
        else:
            print("\n❌ Keine freien Slots verfügbar")

    elif choice == "2":
        show_scheduled_slots()

    elif choice == "3":
        confirm = input("Wirklich alle Slots für heute löschen? (ja/nein): ")
        if confirm.lower() == "ja":
            reset_slots_for_date()
        else:
            print("Abgebrochen.")

    elif choice == "4":
        confirm = input("Wirklich ALLE Slots löschen? (ja/nein): ")
        if confirm.lower() == "ja":
            reset_all_slots()
        else:
            print("Abgebrochen.")

    elif choice == "5":
        print("\nVergebe 5 Test-Slots...")
        for i in range(5):
            slot = next_available_slot(cfg)
            if slot:
                print(f"  {i+1}. Slot vergeben: {slot}")
            else:
                print(f"  {i+1}. Kein Slot mehr verfügbar")
                break
        print("\n✅ Test abgeschlossen. Zeige alle Slots:")
        show_scheduled_slots()

    else:
        print("Ungültige Auswahl.")
