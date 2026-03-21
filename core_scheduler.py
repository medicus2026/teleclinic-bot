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
        return None


def minutes_to_hhmm(m: int) -> str:
    """Wandelt Minuten in HH:MM-Format um."""
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
    Prüft belegte Slots in scheduled_slots.json.
    Erstellt Datei automatisch, wenn nicht vorhanden.

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
    start = hhmm_to_minutes(tf.get("treatment_start", "08:00"))
    end = hhmm_to_minutes(tf.get("treatment_end", "18:00"))

    # Falls min_start_time gesetzt, nutze das als Start (aber nicht vor treatment_start!)
    if min_start_time:
        min_start_minutes = hhmm_to_minutes(min_start_time)
        if min_start_minutes > start:
            start = min_start_minutes
            print(f"[SCHEDULER] Frühester Start angepasst auf: {min_start_time} (wegen Patientenwunsch)")

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

    if not start or not end or start >= end:
        print("[ERROR] Ungültige Start/Endzeit.")
        return None

    print(f"[SCHEDULER] Zeitraum: {minutes_to_hhmm(start)} - {minutes_to_hhmm(end)}, Intervall: {interval} Min.")

    if direction == "backward":
        current = end - interval
        while current >= start:
            t = minutes_to_hhmm(current)
            if t not in today_slots:
                today_slots.append(t)
                today_slots.sort()
                slots[date] = today_slots
                save_slots(slots)
                print(f"[SCHEDULER] ✅ Slot {t} vergeben (rückwärts). Gesamt belegt: {len(today_slots)}")
                return t
            current -= interval
    else:
        # FORWARD: Beginne am Start und gehe vorwärts (9:00, 9:10, 9:20...)
        current = start
        while current < end:
            t = minutes_to_hhmm(current)
            if t not in today_slots:
                today_slots.append(t)
                today_slots.sort()
                slots[date] = today_slots
                save_slots(slots)
                print(f"[SCHEDULER] ✅ Slot {t} vergeben (vorwärts). Gesamt belegt: {len(today_slots)}")
                print(f"[SCHEDULER] Nächster verfügbarer Slot wäre: {minutes_to_hhmm(current + interval)}")
                return t
            else:
                print(f"[SCHEDULER] Slot {t} bereits belegt, prüfe nächsten...")
            current += interval

    print("[WARN] Keine freien Slots mehr verfügbar im Zeitraum.")
    return None


def validate_max_patients(filters: dict) -> tuple[int, int, bool]:
    """
    Validiert die max_patients-Einstellung gegen die verfügbaren Slots.

    Returns:
        (max_patients_requested, max_patients_possible, is_valid)

    Beispiel:
        - Requested: 10, Possible: 36 → (10, 36, True) - OK, setze 10
        - Requested: 50, Possible: 36 → (50, 36, False) - WARNUNG, setze auf 36
        - Requested: 0 oder None → (5, 36, True) - Default 5, OK
    """
    tf = filters.get("time_filter", {})
    rt = filters.get("runtime", {})

    # Lade Max-Patienten
    max_patients_requested = rt.get("max_patients", 5)
    try:
        max_patients_requested = int(max_patients_requested)
    except (ValueError, TypeError):
        max_patients_requested = 5

    if max_patients_requested <= 0:
        max_patients_requested = 5

    # Berechne max möglich
    start = hhmm_to_minutes(tf.get("treatment_start", "08:00"))
    end = hhmm_to_minutes(tf.get("treatment_end", "18:00"))

    interval = rt.get("interval_minutes", 5)
    try:
        interval = int(interval)
    except (ValueError, TypeError):
        interval = 5

    if interval <= 0:
        interval = 5

    max_patients_possible = calculate_max_slots(start, end, interval)

    # Prüfe ob Wunsch erreichbar
    is_valid = max_patients_requested <= max_patients_possible

    if not is_valid:
        print(f"\n{'=' * 70}")
        print(f"⚠️  WARNUNG: Max-Patientenzahl nicht erreichbar!")
        print(f"{'=' * 70}")
        print(f"  Wunsch:    {max_patients_requested} Patienten")
        print(f"  Möglich:   {max_patients_possible} Slots in {minutes_to_hhmm(start)} - {minutes_to_hhmm(end)}")
        print(f"  Intervall: {interval} Minuten")
        print(f"\n  → Setze max_patients auf {max_patients_possible} (erreichbarer Wert)")
        print(f"{'=' * 70}\n")

    return (max_patients_requested, max_patients_possible, is_valid)


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
