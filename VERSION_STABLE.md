STABLE_VERSION_NAME=TeleClinicBot-Stable-2026-02-01-A
STABLE_VERSION_DESC=Stabiler Stand nach Scheduler-Min-Start, Log-Reset, Counter-Fix, Smart-Login-Erkennung, Logo-Anpassung, Live-Terminkalender
STABLE_VERSION_NOTES=Diese Datei dient als Referenz fuer den funktionierenden Stand. Bei Fehlprogrammierung auf diesen Stand zurueckgehen.

FEATURES_IMPLEMENTED:
- Intelligente Chrome-Erkennung (sofortiger Start wenn Chrome laeuft)
- Patient-Counter mit global-Deklaration (3x: handle_case, click_loop, main)
- Log-Datei-Reset beim Bot-Start (keine alten Eintraege)
- Scheduler Auto-Cleanup fuer alte Slots
- Scheduler respektiert Patientenwunsch (min_start_time Parameter)
- Korrekte Scheduler-Intervalle (5 Min + beliebig)
- Live-Terminkalender in GUI mit Uhrzeit, Diagnose, Wunsch, Alter, Geschlecht
- Praxis-Logo in Header
- Intelligente Filter-Synonyme (Akne->Haut, AU->Arbeitsunfaehigkeit, etc.)
- Case-insensitive Matching
- Fehlerbehandlung und Stability

SNAPSHOT_LOCATION=C:\teleclinic-bot\TeleClinicBot-Stable-2026-02-01-A.zip
REFERENZDATEI=C:\teleclinic-bot\VERSION_STABLE.md

