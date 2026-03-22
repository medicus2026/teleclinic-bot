✅ PHASE 1 — ABGESCHLOSSEN
═══════════════════════════════════════════════════════════════════════════════

🎯 FERTIG GESTELLT (Schritt 1–3 aus dem Plan):
  ✅ Migrations-Funktion (alte → neue filters.json Format)
  ✅ GUI umgestaltet: Slot-1-Block + Checkbox + aufklappbarer Slot-2-Block
  ✅ load_filters() angepasst (lädt neues Format + migriert automatisch)
  ✅ save_filters() angepasst (speichert beide Slots separat)
  ✅ toggle_slot2() Funktion (zeigt/versteckt Slot-2-Bereich)
  ✅ Test durchgeführt (Migration funktioniert ✅)
  ✅ Git-Commit abgeschlossen

═══════════════════════════════════════════════════════════════════════════════

📊 WAS HAT SICH GEÄNDERT:

**filters.json Format (alt → neu):**

  ALT (flach):
    time_filter: { treatment_start, treatment_end, treatment_start_2, treatment_end_2 }
    runtime: { max_patients, interval_minutes, ... }
    patients: { gender, age_min, age_max, language_include, language_exclude }
    diagnosis: { include, exclude }
    wishes: { include, exclude }

  NEU (pro Slot):
    time_filter: { day_window }
    slot1: { time_start, time_end, max_patients, diagnosis_include, diagnosis_exclude, 
             wishes_include, wishes_exclude, language_include, language_exclude, 
             age_min, age_max, gender }
    slot2_enabled: false
    slot2: { ...wie slot1... }
    runtime: { interval_minutes, headless, slowmo_ms }
    loop: { scan_interval_sec, max_pages }

**GUI Layout:**

  Vorher:
    - Flache Anordnung aller Filter
    - Zeit von 2 war optional, aber hatte keine eigenen Filter

  Nachher:
    - 🕐 SLOT 1 (Vormittag) — komplette Filtergruppe
    - ☐ CHECKBOX: „2. Zeitslot aktivieren"
    - 🕑 SLOT 2 (Nachmittag) — komplette Filtergruppe (versteckt, bis Checkbox aktiv)
    - ⚙️ ALLGEMEINE EINSTELLUNGEN (Scan-Intervall, etc.)

**Datenintegrität:**

  • Migration: Alte Filter werden automatisch in slot1 verschoben
  • Keine Datenverluste (Zeit-Slot 2 wird in slot2.time_start/.time_end übernommen)
  • slot2_enabled startet mit false → Verhalten wie bisher, bis Benutzer aktiviert
  • Rückwärtskompatibel: Alte filters.json funktioniert nach Upgrade ohne Eingriff

═══════════════════════════════════════════════════════════════════════════════

✨ JETZT FUNKTIONIERT BEREITS:

  1️⃣  GUI startet → laden alte filters.json ✅
  2️⃣  Automatisch migriert zu neuem Format ✅
  3️⃣  Checkbox „2. Zeitslot aktivieren" ist da (aber deaktiviert) ✅
  4️⃣  Wenn an: Slot-2-Block wird sichtbar ✅
  5️⃣  Filter speichern → speichert beide Slots ✅
  6️⃣  Filter laden → lädt beide Slots ✅

═══════════════════════════════════════════════════════════════════════════════

🔄 NÄCHSTE PHASE (Schritt 4–5): BOT-LOGIK

  Kommende Änderungen in teleclinic_click_from_list_v9d.py:
    [ ] build_slot_filters() — Konvertiert Slot-Daten zu altem Filter-Format
    [ ] Slot-Routing in click_loop() — Prüfe Fall gegen beide Slots
    [ ] Pro-Slot-Zähler (slot1_accepted, slot2_accepted)
    [ ] Stop-Bedingung anpassen: beide Slots voll statt nur einer

  Geschätzter Aufwand: ~1,5 Stunden

═══════════════════════════════════════════════════════════════════════════════

🧪 ZUM TESTEN (jetzt möglich):

  python C:\teleclinic-bot\test_gui_slot2_migration.py
  → Zeigt Migration der aktuellen filters.json

  Auch in der GUI (wenn gestartet):
  1. Starte GUI: python tc_main_gui.py
  2. Checkbox aktivieren → Slot-2-Block erscheint
  3. Werte ändern in Slot 1 + Slot 2
  4. 💾 Filter speichern
  5. GUI neustarten → Werte sind noch da, Slot-2-Block bleibt verborgen (weil Checkbox nicht aktiv in den gespeicherten Daten)
  6. Checkbox aktivieren → Slot-2-Werte sind noch da!

═══════════════════════════════════════════════════════════════════════════════

💾 GIT-COMMIT:
  ✅ [backup/pro-slot-pre-fix-20260322-0910 87dbde6]
     feat: GUI Slot-2-Erweiterung Phase 1 - Migrations + UI Layout
     3 files changed, 762 insertions(+)

═══════════════════════════════════════════════════════════════════════════════

⚡ ALLES STABIL (NICHT GEÄNDERT):

  ✅ teleclinic_click_from_list_v9d.py (noch unverändert)
  ✅ core_scheduler.py (noch unverändert)
  ✅ Lizenz-System
  ✅ Terminkalender-Logik
  ✅ Playwright-Connection
  ✅ Chrome-Debug-Modus

═══════════════════════════════════════════════════════════════════════════════
