#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scheduled_patients.py - Speichert terminierte Patienten mit vollständigen Daten
"""

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
PATIENTS_FILE = ROOT / "scheduled_patients.json"


def load_patients() -> dict:
    """Lädt gespeicherte Patienten oder gibt leere Struktur zurück."""
    if not PATIENTS_FILE.exists():
        return {}

    try:
        with open(PATIENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_patients(patients: dict) -> None:
    """Speichert Patienten atomar."""
    try:
        tmp = PATIENTS_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(patients, f, indent=2, ensure_ascii=False)
        tmp.replace(PATIENTS_FILE)
    except Exception as e:
        print(f"[ERROR] Fehler beim Speichern von Patienten: {e}")


def add_patient(time: str, diagnosis: str, wishes: str, gender: str, age: int | str,
                date: str | None = None) -> None:
    """Fügt einen terminierten Patienten hinzu."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    patients = load_patients()

    if date not in patients:
        patients[date] = {}

    if time not in patients[date]:
        patients[date][time] = {
            "diagnosis": diagnosis,
            "wishes": wishes,
            "gender": gender,
            "age": str(age) if age else "",
            "timestamp": datetime.now().isoformat(),
            "source": "bot"
        }
        save_patients(patients)
        print(f"[PATIENT] ✅ Patient {time} gespeichert: {diagnosis}")
    else:
        existing = patients[date][time]
        if existing.get("source") == "teleclinic_import":
            patients[date][time] = {
                "diagnosis": diagnosis,
                "wishes": wishes,
                "gender": gender,
                "age": str(age) if age else "",
                "timestamp": datetime.now().isoformat(),
                "source": "bot"
            }
            save_patients(patients)
            print(f"[PATIENT] ✅ Import-Platzhalter {time} mit echten Patientendaten ersetzt")
        else:
            print(f"[PATIENT] ⚠️ Zeit {time} bereits belegt")


def add_imported_appointment(time: str, date: str | None = None,
                             diagnosis: str = "Extern terminiert",
                             wishes: str = "",
                             gender: str = "",
                             age: str = "") -> None:
    """Fügt einen extern bereits vorhandenen Termin als Platzhalter für den GUI-Kalender hinzu.

    Wenn echte Patientendaten übergeben werden (diagnosis, wishes, gender, age),
    werden diese gespeichert. Andernfalls wird ein Platzhalter eingetragen.
    Bereits vom Bot gesetzte Termine (source='bot') werden NICHT überschrieben.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    patients = load_patients()
    if date not in patients:
        patients[date] = {}

    existing = patients[date].get(time)
    if existing:
        if existing.get("source") == "bot":
            # Bot-Termin hat immer Vorrang — nie überschreiben
            return
        if existing.get("source") == "teleclinic_import":
            # Immer aktualisieren mit den aktuellsten Daten aus Teleclinic
            patients[date][time].update({
                "diagnosis": diagnosis if diagnosis else existing.get("diagnosis", ""),
                "wishes": wishes if wishes else existing.get("wishes", ""),
                "gender": gender if gender else existing.get("gender", ""),
                "age": age if age else existing.get("age", ""),
                "timestamp": datetime.now().isoformat(),
            })
            save_patients(patients)
            print(f"[PATIENT] ℹ️ Externer Termin {time} aktualisiert: {diagnosis} | {gender} | {age}J")
            return

    patients[date][time] = {
        "diagnosis": diagnosis,
        "wishes": wishes,
        "gender": gender,
        "age": age,
        "timestamp": datetime.now().isoformat(),
        "source": "teleclinic_import"
    }
    save_patients(patients)
    print(f"[PATIENT] ℹ️ Externer Termin {time} im Kalender gespiegelt: {diagnosis}")


def get_patients_for_date(date: str | None = None) -> dict:
    """Gibt alle Patienten für ein bestimmtes Datum zurück."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    patients = load_patients()
    return patients.get(date, {})


def reset_patients_for_date(date: str | None = None, keep_imported: bool = False) -> None:
    """Löscht alle Patienten für ein bestimmtes Datum."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    patients = load_patients()
    if date in patients:
        if keep_imported:
            imported_only = {
                time: patient
                for time, patient in patients[date].items()
                if patient.get("source") == "teleclinic_import"
            }
            if imported_only:
                patients[date] = imported_only
                save_patients(patients)
                print(f"[PATIENT] ✅ Bot-Patienten für {date} gelöscht, importierte Termine behalten")
            else:
                del patients[date]
                save_patients(patients)
                print(f"[PATIENT] ✅ Alle Patienten für {date} gelöscht")
        else:
            del patients[date]
            save_patients(patients)
            print(f"[PATIENT] ✅ Alle Patienten für {date} gelöscht")


def reset_all_patients() -> None:
    """Löscht ALLE Patienten."""
    save_patients({})
    print("[PATIENT] ✅ Alle Patienten gelöscht")


if __name__ == "__main__":
    # Test
    print("Test scheduled_patients.py")
    add_patient("11:00", "Psychische Leiden", "", "weiblich", "32")
    add_patient("11:05", "Psychische Leiden", "", "männlich", "26")

    patients = get_patients_for_date()
    print(f"\nGespeicherte Patienten: {json.dumps(patients, indent=2, ensure_ascii=False)}")
