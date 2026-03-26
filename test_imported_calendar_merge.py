#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kleiner Regressionstest für importierte externe Termine im GUI-Kalender."""

from scheduled_patients import (
    add_imported_appointment,
    add_patient,
    get_patients_for_date,
    reset_patients_for_date,
)


def main():
    test_date = "2099-12-31"

    # sauberer Start
    reset_patients_for_date(test_date)

    # 1) externer Termin erscheint als Platzhalter (ohne Daten)
    add_imported_appointment("18:00", date=test_date)
    patients = get_patients_for_date(test_date)
    assert "18:00" in patients, "Importierter Termin fehlt"
    assert patients["18:00"]["source"] == "teleclinic_import"

    # 1b) externer Termin mit echten Patientendaten
    add_imported_appointment("17:00", date=test_date,
                             diagnosis="Rückenschmerzen", wishes="Rezept",
                             gender="weiblich", age="42")
    patients = get_patients_for_date(test_date)
    assert "17:00" in patients, "Importierter Termin mit Daten fehlt"
    assert patients["17:00"]["source"] == "teleclinic_import"
    assert patients["17:00"]["diagnosis"] == "Rückenschmerzen", "Diagnose nicht gespeichert"
    assert patients["17:00"]["wishes"] == "Rezept", "Wünsche nicht gespeichert"
    assert patients["17:00"]["gender"] == "weiblich", "Geschlecht nicht gespeichert"
    assert patients["17:00"]["age"] == "42", "Alter nicht gespeichert"

    # 1c) Platzhalter (18:00) kann mit echten Daten aktualisiert werden
    add_imported_appointment("18:00", date=test_date,
                             diagnosis="Husten", wishes="AU")
    patients = get_patients_for_date(test_date)
    assert patients["18:00"]["diagnosis"] == "Husten", "Platzhalter wurde nicht mit echten Daten aktualisiert"

    # 2) echter Bot-Patient überschreibt den Platzhalter auf derselben Uhrzeit
    add_patient("18:00", "Muskelschmerzen", "REZEPT", "männlich", 26, date=test_date)
    patients = get_patients_for_date(test_date)
    assert patients["18:00"]["source"] == "bot", "Bot-Daten haben Import-Platzhalter nicht ersetzt"
    assert patients["18:00"]["diagnosis"] == "Muskelschmerzen"

    # 2b) Bot-Termin wird durch add_imported_appointment NICHT überschrieben
    add_imported_appointment("18:00", date=test_date, diagnosis="Sollte ignoriert werden")
    patients = get_patients_for_date(test_date)
    assert patients["18:00"]["source"] == "bot", "Bot-Termin wurde fälschlich durch Import überschrieben"
    assert patients["18:00"]["diagnosis"] == "Muskelschmerzen"

    # 3) zusätzlicher externer Termin bleibt beim selektiven Reset erhalten
    add_imported_appointment("19:00", date=test_date)
    reset_patients_for_date(test_date, keep_imported=True)
    patients = get_patients_for_date(test_date)
    assert "18:00" not in patients, "Bot-Termin wurde beim keep_imported-Reset nicht entfernt"
    assert "19:00" in patients, "Importierter Termin wurde fälschlich entfernt"
    assert patients["19:00"]["source"] == "teleclinic_import"

    # Aufräumen
    reset_patients_for_date(test_date)
    print("OK - importierte Termine werden gespiegelt, echte Daten gespeichert, Bot-Daten überschreiben Platzhalter, keep_imported funktioniert")


if __name__ == "__main__":
    main()
