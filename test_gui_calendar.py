#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: GUI Terminkalender zeigt korrekte Daten
Simuliert mehrere geklickte Patienten und prüft die Anzeige
"""

import sys
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def create_test_patients():
    """Erstelle Test-Patienten in scheduled_patients.json"""
    from scheduled_patients import save_patients

    today = datetime.now().strftime("%Y-%m-%d")

    test_data = {
        today: {
            "12:00": {
                "diagnosis": "Hautkrankheiten",
                "wishes": "AU, Rezept",
                "gender": "weiblich",
                "age": "28",
                "timestamp": datetime.now().isoformat()
            },
            "12:05": {
                "diagnosis": "Akne",
                "wishes": "Beratung",
                "gender": "männlich",
                "age": "22",
                "timestamp": datetime.now().isoformat()
            },
            "12:10": {
                "diagnosis": "Psoriasis",
                "wishes": "Rezept",
                "gender": "weiblich",
                "age": "35",
                "timestamp": datetime.now().isoformat()
            }
        }
    }

    save_patients(test_data)
    print(f"✅ Test-Patienten erstellt für {today}:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))

def test_extraction():
    """Teste die _extract_and_add_appointment Methode"""
    from tc_main_gui import TeleClinicBotGUI
    import tkinter as tk

    print("\n" + "="*60)
    print("TEST: _extract_and_add_appointment mit 3 Patienten")
    print("="*60)

    # Erstelle GUI-Instanz (ohne mainloop)
    root = tk.Tk()
    root.withdraw()  # Verstecke Fenster

    gui = TeleClinicBotGUI(root)

    # Simuliere appointments-Liste
    appointments = []

    # Rufe Extraktions-Methode auf
    gui._extract_and_add_appointment(appointments)

    print(f"\nAnzahl Termine in appointments: {len(appointments)}")
    print("\nTerminkalender-Inhalt:")
    print("-" * 60)

    for i, appt in enumerate(appointments, 1):
        print(f"{i}. {appt['time']} | {appt['diagnosis']} | {appt['wishes']} | {appt['gender']} | {appt['age']}J")

    print("-" * 60)

    # Validierung
    if len(appointments) == 3:
        print("\n✅ ERFOLG: 3 Patienten korrekt geladen!")

        # Prüfe ob unterschiedliche Diagnosen vorhanden sind
        diagnoses = [a['diagnosis'] for a in appointments]
        if len(set(diagnoses)) == 3:
            print("✅ ERFOLG: Alle 3 Diagnosen sind unterschiedlich!")
        else:
            print("❌ FEHLER: Duplikate gefunden:", diagnoses)
            return False

        # Prüfe Uhrzeiten
        times = [a['time'] for a in appointments]
        expected = ["12:00", "12:05", "12:10"]
        if times == expected:
            print(f"✅ ERFOLG: Uhrzeiten korrekt: {times}")
        else:
            print(f"❌ FEHLER: Uhrzeiten falsch. Erwartet: {expected}, Gefunden: {times}")
            return False

        return True
    else:
        print(f"❌ FEHLER: Falsche Anzahl. Erwartet: 3, Gefunden: {len(appointments)}")
        return False

def cleanup():
    """Räume Test-Daten auf"""
    from scheduled_patients import reset_all_patients
    reset_all_patients()
    print("\n🧹 Test-Daten bereinigt")

if __name__ == "__main__":
    print("="*60)
    print("GUI TERMINKALENDER - TEST")
    print("="*60)

    try:
        # 1. Erstelle Test-Daten
        create_test_patients()

        # 2. Teste Extraktion
        success = test_extraction()

        # 3. Aufräumen
        cleanup()

        # Ergebnis
        print("\n" + "="*60)
        if success:
            print("✅ TEST BESTANDEN - Terminkalender funktioniert korrekt!")
        else:
            print("❌ TEST FEHLGESCHLAGEN")
        print("="*60)

    except Exception as e:
        print(f"\n❌ TEST-FEHLER: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
