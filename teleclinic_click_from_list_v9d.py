# teleclinic_click_from_list_v9d.py
# Vollständige, überarbeitete Version mit Scheduler-Integration
# Asynchrone Version (Playwright async_api)

import asyncio
import json
import subprocess
import sys
import time
import threading
import re
import re as _re
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Scheduler-Modul
from core_scheduler import next_available_slot, confirm_slot, validate_max_patients, reset_slots_for_date, load_slots, save_slots

ROOT = Path(__file__).resolve().parent
FILTER_PATH = ROOT / "filters.json"
LOG_PATH = ROOT / "tc_click_log.txt"

# Globale Variable für den manuellen Start
manual_start = False

# Globaler Counter für übernommene Patienten
patients_accepted = 0


def normalize_text(text: str) -> str:
    """Normalisiert Text für case-insensitive Vergleiche (casefold + Whitespace-Trim)."""
    return " ".join((text or "").split()).casefold()


def word_boundary_match(text: str, term: str) -> bool:
    """
    Prüft, ob ein Begriff als ganzes Wort im Text vorkommt (Word Boundary).

    Beispiele:
    - word_boundary_match("AU-Bescheinigung", "au") → True ✅
    - word_boundary_match("Hautkrankheiten", "au") → False ❌
    - word_boundary_match("ich brauche AU", "au") → True ✅

    Wichtig für Begriffe wie "AU" die sonst in "Haut" etc. matchen würden!
    """
    import re
    # \b = Word Boundary (Wortgrenze)
    pattern = r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


async def log_line(text: str):
    """Schreibt Logzeile mit Zeitstempel."""
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))
    LOG_PATH.write_text(LOG_PATH.read_text(encoding="utf-8") + "\n" + line if LOG_PATH.exists() else line, encoding="utf-8")


async def load_filters() -> dict:
    """Lädt Filterparameter."""
    if not FILTER_PATH.exists():
        await log_line("[ERROR] filters.json nicht gefunden – Abbruch.")
        return {}
    try:
        data = json.loads(FILTER_PATH.read_text(encoding="utf-8"))
        await log_line("[INFO] Filter geladen.")
        return data
    except Exception as e:
        await log_line(f"[ERROR] Konnte Filter nicht laden: {e}")
        return {}


def get_tab_number(day_window: str) -> int:
    """Bestimmt tab-Nummer für day_window (0=heute, 1=morgen, 2=später)"""
    dw = normalize_text(day_window)
    if dw == "morgen":
        return 1
    elif dw == "später":
        return 2
    else:
        return 0


async def validate_and_fix_day_filter(page, day_window: str):
    """
    HYBRID-ANSATZ für maximale Stabilität:
    1. Primär: URL-Navigation mit tab-Parameter
    2. Validierung: Prüfe Button-Text
    3. Fallback: Button-Klick falls URL-Methode nicht funktioniert
    """
    dw = normalize_text(day_window)
    if not dw or dw == "heute":
        expected_text = "Heute"
    elif dw == "morgen":
        expected_text = "Morgen"
    else:
        expected_text = "Später"

    try:
        # Prüfe ob Datumsfilter-Button existiert und seinen Text
        btn = page.locator("[data-testid='filter-date']").first
        if not await btn.count():
            await log_line("[FILTER] ⚠️ Datumsfilter-Button nicht gefunden - überspringe Validierung")
            return True  # Verlasse uns auf URL

        current_text = await btn.inner_text()
        current_text = current_text.strip()

        await log_line(f"[FILTER] Validierung: Button zeigt '{current_text}', erwartet '{expected_text}'")

        # Wenn Button-Text stimmt, alles gut
        if expected_text.lower() in current_text.lower():
            await log_line(f"[FILTER] ✅ Datumsfilter korrekt: '{expected_text}'")
            return True

        # FALLBACK: Button-Text stimmt nicht, versuche Button-Klick
        await log_line(f"[FILTER] ⚠️ URL-Tab-Methode funktioniert nicht! Fallback auf Button-Klick...")

        # Button klicken
        await btn.click(timeout=5000)
        await page.wait_for_timeout(300)

        # Warte auf Menü
        try:
            await page.wait_for_selector("div[role='menu']", state="visible", timeout=2000)
        except Exception:
            await log_line("[FILTER] ⚠️ Menü erschien nicht - möglicherweise bereits gesetzt")
            return False

        await page.wait_for_timeout(200)

        # Suche Menüeintrag
        items = await page.locator("[role='menuitem']").all()
        await log_line(f"[FILTER] Suche '{expected_text}' in {len(items)} Menüeinträgen...")

        target_item = None
        for item in items:
            try:
                item_text = await item.inner_text()
                if expected_text.lower() in item_text.lower():
                    target_item = item
                    await log_line(f"[FILTER] ✓ Gefunden: '{item_text}'")
                    break
            except Exception:
                continue

        if not target_item:
            await log_line(f"[FILTER] ❌ Menüeintrag '{expected_text}' nicht gefunden!")
            await page.keyboard.press("Escape")
            return False

        # Klicke Menüeintrag
        await target_item.click(timeout=5000)
        await page.wait_for_timeout(300)

        # Verifiziere
        new_text = await btn.inner_text()
        if expected_text.lower() in new_text.lower():
            await log_line(f"[FILTER] ✅ Button-Klick erfolgreich: '{new_text}'")
            return True
        else:
            await log_line(f"[FILTER] ⚠️ Button-Klick evtl. fehlgeschlagen: '{new_text}'")
            return False

    except Exception as e:
        await log_line(f"[FILTER] ❌ Fehler bei Validierung/Fallback: {e}")
        return False


def wait_for_enter():
    """Wartet auf ENTER-Taste in separatem Thread."""
    global manual_start
    try:
        input()  # Blockiert bis ENTER gedrückt wird
        manual_start = True
    except (EOFError, OSError):
        # Kein echtes stdin (GUI-Subprocess mit DEVNULL) → sofort starten
        manual_start = True


def parse_time_range(text: str) -> tuple:
    """
    Extrahiert Zeitraum aus Text wie "16:00 - 18:00" (24h) oder "10:00 PM - 12:00 AM" (12h).
    Returns: (start_minutes, end_minutes) oder (None, None)

    Unterstützt:
    - 24h-Format: "16:00 - 18:00" ✅
    - 12h-Format: "4:00 PM - 6:00 PM" ✅
    - Gemischt: "10:00 PM - 12:00 AM" ✅ (auch über Mitternacht)
    - Mit Datumswechsel: "Heute, 22:00 - Morgen, 00:00" ✅
    """
    import re

    # Entferne Datums-Präfixe (Heute, Morgen, etc.) für einfacheres Matching
    text_cleaned = re.sub(r'(Heute|Today|Morgen|Tomorrow|Später|Later|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mo|Di|Mi|Do|Fr|Sa|So|[A-Z][a-z]+day),?\s*', '', text, flags=re.IGNORECASE)

    # Pattern für 24h-Format: "HH:MM - HH:MM"
    match_24h = re.search(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})(?!\s*[APap])', text_cleaned)
    if match_24h:
        start_h, start_m, end_h, end_m = map(int, match_24h.groups())
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        # Fix: Über-Mitternacht-Fall (z.B. 22:00 - 00:00 oder 23:00 - 01:00)
        # 00:00 als Ende = 1440 Minuten (= nächster Tag 00:00)
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        return (start_minutes, end_minutes)

    # Pattern für 12h-Format: "H:MM AM/PM - H:MM AM/PM"
    match_12h = re.search(
        r'(\d{1,2}):(\d{2})\s*([APap][Mm])\s*-\s*(\d{1,2}):(\d{2})\s*([APap][Mm])',
        text_cleaned
    )
    if match_12h:
        start_h, start_m, start_ampm, end_h, end_m, end_ampm = match_12h.groups()
        start_h, start_m, end_h, end_m = map(int, [start_h, start_m, end_h, end_m])

        # Konvertiere 12h zu 24h
        if start_ampm.upper() == 'PM' and start_h != 12:
            start_h += 12
        elif start_ampm.upper() == 'AM' and start_h == 12:
            start_h = 0

        if end_ampm.upper() == 'PM' and end_h != 12:
            end_h += 12
        elif end_ampm.upper() == 'AM' and end_h == 12:
            end_h = 0

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # Wenn Endzeit < Startzeit, bedeutet es über Mitternacht (z.B. 10 PM - 2 AM)
        # In diesem Fall addiere 24h zur Endzeit
        if end_minutes < start_minutes:
            end_minutes += 24 * 60

        return (start_minutes, end_minutes)

    return (None, None)


def calculate_overlap_start(patient_start: int, patient_end: int,
                            treatment_start: int, treatment_end: int) -> str:
    """
    Berechnet die Startzeit in der Überschneidung zweier Zeiträume.

    patient_start/end: Patientenwunsch in Minuten (z.B. 16:00 = 960)
    treatment_start/end: Sprechstundenzeit in Minuten (z.B. 19:00 = 1140)

    Returns: HH:MM String der Startzeit in der Überschneidung, oder None
    """
    # Prüfe ob es Überschneidung gibt
    if patient_end <= treatment_start or patient_start >= treatment_end:
        return None  # Keine Überschneidung

    # Startzeit ist das Maximum der beiden Startzeiten
    overlap_start = max(patient_start, treatment_start)

    # Konvertiere zurück zu HH:MM
    hours = overlap_start // 60
    minutes = overlap_start % 60
    return f"{hours:02d}:{minutes:02d}"


def time_to_minutes(time_str: str) -> int:
    """Konvertiert HH:MM zu Minuten."""
    try:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    except:
        return None


def normalize_term(term: str) -> list:
    """
    Normalisiert einen Term und gibt alle erkannten Synonyme zurück.

    WICHTIG: Unterscheidung zwischen generischen und spezifischen Diagnosen!
    - "Derma", "Dermatologisch" → Alle Hautkrankheiten
    - "Akne", "Psoriasis", "Pilz" → Nur spezifische Synonyme

    Beispiele:
    - "derma" → ALLE Hautkrankheiten (Wildcard)
    - "akne" → nur ["akne", "pickel", "acne"]
    - "au" → ["au", "arbeitsunfähigkeit", "krankmeldung"]
    - "englisch" → ["englisch", "english"]
    """
    term_lower = normalize_text(term)

    # WICHTIG: Generische Haut-Begriffe (Wildcard für ALLE Hauterkrankungen)
    HAUT_GENERISCH = [
        "hautkrankheit", "hautkrankheiten", "haut",
        "derma", "dermat", "dermatolog", "dermatologisch",
        "skin", "hauterkrankung", "hauterkrankungen"
    ]

    # Spezifische Erkrankungen (matchen NUR sich selbst + direkte Synonyme)
    AKNE_GRUPPE = ["akne", "acne", "pickel", "pimple"]
    PSORIASIS_GRUPPE = ["psoriasis", "schuppenflechte"]
    PILZ_GRUPPE = ["pilz", "pilzinfektion", "fungal", "mykose"]
    EKZEM_GRUPPE = ["ekzem", "eczema", "neurodermitis", "atopische dermatitis"]
    JUCKREIZ_GRUPPE = ["juckreiz", "itching", "jucken", "kratzen"]
    AUSSCHLAG_GRUPPE = ["ausschlag", "rash", "exanthem", "rötung", "erythem"]

    # ALLE Hauterkrankungen zusammen (für generische Suche: "Derma", "Haut")
    ALLE_HAUT_ERKRANKUNGEN = list(set(
        HAUT_GENERISCH + AKNE_GRUPPE + PSORIASIS_GRUPPE + PILZ_GRUPPE +
        EKZEM_GRUPPE + JUCKREIZ_GRUPPE + AUSSCHLAG_GRUPPE
    ))

    # Schlafstörungen / Schlaf-Probleme
    SCHLAF_GRUPPE = [
        "schlafstörung", "schlafstörungen", "schlafstoerung", "schlafstoerungen",
        "schlaf", "insomnie", "insomnia", "durchschlaf", "einschlaf", "wachliegen"
    ]

    # Geschlechtskrankheiten / sexuelle Gesundheit / erektile Dysfunktion
    SEXUAL_GESUNDHEIT = [
        "geschlechtskrankheit", "geschlechtskrankheiten", "sexuell übertrag", "sexuell uebertrag", "sti", "std",
        "gonorrhoe", "chlamydien", "syphilis", "tripper", "genitalherpes", "herpes genital",
        "urethritis", "harnröhrenentzündung", "harnroehrenentzuendung",
        "erektile dysfunktion", "erektionsstörung", "erektionsstoerung", "potenzstörung", "erectile dysfunction", "impotenz"
    ]

    DIAGNOSIS_SYNONYMS = {
        # GENERISCHE Haut-Begriffe → ALLE Hautkrankheiten
        "haut": ALLE_HAUT_ERKRANKUNGEN,
        "hautkrankheit": ALLE_HAUT_ERKRANKUNGEN,
        "hautkrankheiten": ALLE_HAUT_ERKRANKUNGEN,
        "derma": ALLE_HAUT_ERKRANKUNGEN,
        "dermat": ALLE_HAUT_ERKRANKUNGEN,
        "dermatolog": ALLE_HAUT_ERKRANKUNGEN,
        "dermatologisch": ALLE_HAUT_ERKRANKUNGEN,
        "skin": ALLE_HAUT_ERKRANKUNGEN,
        "hauterkrankung": ALLE_HAUT_ERKRANKUNGEN,

        # SPEZIFISCHE Diagnosen → Nur eigene Synonyme
        "akne": AKNE_GRUPPE,
        "acne": AKNE_GRUPPE,
        "pickel": AKNE_GRUPPE,
        "pimple": AKNE_GRUPPE,

        "psoriasis": PSORIASIS_GRUPPE,
        "schuppenflechte": PSORIASIS_GRUPPE,

        "pilz": PILZ_GRUPPE,
        "pilzinfektion": PILZ_GRUPPE,
        "fungal": PILZ_GRUPPE,
        "mykose": PILZ_GRUPPE,

        "ekzem": EKZEM_GRUPPE,
        "eczema": EKZEM_GRUPPE,
        "neurodermitis": EKZEM_GRUPPE,
        "atopische": EKZEM_GRUPPE,

        "juckreiz": JUCKREIZ_GRUPPE,
        "itching": JUCKREIZ_GRUPPE,
        "jucken": JUCKREIZ_GRUPPE,

        "ausschlag": AUSSCHLAG_GRUPPE,
        "rash": AUSSCHLAG_GRUPPE,
        "exanthem": AUSSCHLAG_GRUPPE,

        # Schlafstörungen
        "schlaf": SCHLAF_GRUPPE,
        "schlafstörung": SCHLAF_GRUPPE,
        "schlafstörungen": SCHLAF_GRUPPE,
        "schlafstoerung": SCHLAF_GRUPPE,
        "insomnie": SCHLAF_GRUPPE,
        "insomnia": SCHLAF_GRUPPE,


        # Geschlechtskrankheiten / ED
        "geschlecht": SEXUAL_GESUNDHEIT,
        "geschlechtskrankheit": SEXUAL_GESUNDHEIT,
        "geschlechtskrankheiten": SEXUAL_GESUNDHEIT,
        "sti": SEXUAL_GESUNDHEIT,
        "std": SEXUAL_GESUNDHEIT,
        "erektile dysfunktion": SEXUAL_GESUNDHEIT,
        "erektionsstörung": SEXUAL_GESUNDHEIT,
        "erektionsstoerung": SEXUAL_GESUNDHEIT,
        "potenzstörung": SEXUAL_GESUNDHEIT,
        "erectile dysfunction": SEXUAL_GESUNDHEIT,
        "impotenz": SEXUAL_GESUNDHEIT,

        "grippaler infekt": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],
        "grippe": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],
        "erkältung": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],
        "husten": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],
        "schnupfen": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],
        "atemwege": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],
        "respiratorisch": ["grippaler infekt", "grippe", "erkältung", "husten", "schnupfen", "respiratorisch", "atemwege"],

        "psychische leiden": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "depression": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "angst": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "stress": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "burnout": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "psych": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "psyche": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
        "psychisch": ["psychische leiden", "depression", "angst", "stress", "burnout", "psych", "psyche", "psychisch"],
    }

    # Wunsch-Synonyme
    WISH_SYNONYMS = {
        "au": ["au", "arbeitsunfähigkeit", "arbeitsunfähigkeitsbescheinigung", "krankmeldung", "krankschreibung"],
        "arbeitsunfähigkeit": ["au", "arbeitsunfähigkeit", "arbeitsunfähigkeitsbescheinigung", "krankmeldung", "krankschreibung"],
        "arbeitsunfähigkeitsbescheinigung": ["au", "arbeitsunfähigkeit", "arbeitsunfähigkeitsbescheinigung", "krankmeldung", "krankschreibung"],
        "krankmeldung": ["au", "arbeitsunfähigkeit", "arbeitsunfähigkeitsbescheinigung", "krankmeldung", "krankschreibung"],
        "krankschreibung": ["au", "arbeitsunfähigkeit", "arbeitsunfähigkeitsbescheinigung", "krankmeldung", "krankschreibung"],

        "rezept": ["rezept", "medikament"],
        "medikament": ["rezept", "medikament"],

        "beratung": ["beratung", "beratungsgespräch"],
        "beratungsgespräch": ["beratung", "beratungsgespräch"],
    }

    # Sprachen-Synonyme
    LANGUAGE_SYNONYMS = {
        "deutsch": ["deutsch", "german"],
        "german": ["deutsch", "german"],

        "englisch": ["englisch", "english"],
        "english": ["englisch", "english"],

        "französisch": ["französisch", "french"],
        "french": ["französisch", "french"],

        "spanisch": ["spanisch", "spanish"],
        "spanish": ["spanisch", "spanish"],
    }

    # Suche in allen Synonym-Dicts - WICHTIG: Nur exakte Key-Matches!
    # Das verhindert, dass "akne" alle Hauterkrankungen matched (weil akne Teil davon ist)
    for key, synonyms in DIAGNOSIS_SYNONYMS.items():
        if term_lower == normalize_text(key):
            return synonyms

    for key, synonyms in WISH_SYNONYMS.items():
        if term_lower == normalize_text(key):
            return synonyms

    for key, synonyms in LANGUAGE_SYNONYMS.items():
        if term_lower == normalize_text(key):
            return synonyms

    # Falls nicht in Synonym-Dict: return den original term (für Custom-Eingaben)
    return [term_lower]


async def check_case_matches_filters(case_element, filters):
    """
    Prüft, ob ein Fall den Filterkriterien entspricht.
    Liest die Falldaten aus dem DOM und vergleicht mit Filtern.

    Returns: (bool, overlap_start_time) - (Passt zu Filtern?, Berechnete Startzeit oder None)
    """
    try:
        # KORREKTUR: Parent-Element enthält die Diagnose-Überschrift!
        parent = await case_element.evaluate_handle('el => el.parentElement')
        case_text = await parent.evaluate('el => el.innerText')
        case_text_lower = normalize_text(case_text)

        await log_line(f"[FILTER] Prüfe Fall: {case_text[:100]}...")

        # ZEIT-FILTER: Prüfe Überschneidung mit einem oder zwei Sprechstunden-Zeitfenstern
        overlap_start_time = None
        patient_start, patient_end = parse_time_range(case_text)
        # WICHTIG: Explizite None-Prüfung, nicht "if patient_start and patient_end"!
        # Grund: patient_end = 0 (Mitternacht) ist falsy, würde übersprungen
        if patient_start is not None and patient_end is not None:
            time_filter = filters.get('time_filter', {})

            # Slot 1 ist verpflichtend, Slot 2 optional
            slot_ranges = []
            t1_start = time_filter.get('treatment_start', '')
            t1_end = time_filter.get('treatment_end', '')
            if t1_start and t1_end:
                slot_ranges.append((t1_start, t1_end, "Slot 1"))

            t2_start = time_filter.get('treatment_start_2', '')
            t2_end = time_filter.get('treatment_end_2', '')
            if t2_start and t2_end:
                slot_ranges.append((t2_start, t2_end, "Slot 2"))

            # Wenn keine Zeitfilter gesetzt: Zeit-Prüfung überspringen (kein Fallback!)
            if not slot_ranges:
                await log_line("[FILTER] ℹ️ Kein Zeitfilter gesetzt – Zeit-Prüfung übersprungen")
                # overlap_start_time bleibt None → kein Zeitfenster erzwingen
            else:
                candidate_starts = []
                for start_str, end_str, slot_name in slot_ranges:
                    treatment_start = time_to_minutes(start_str)
                    treatment_end = time_to_minutes(end_str)
                    if treatment_start is None or treatment_end is None:
                        continue

                    overlap_candidate = calculate_overlap_start(
                        patient_start,
                        patient_end,
                        treatment_start,
                        treatment_end
                    )
                    if overlap_candidate:
                        candidate_starts.append((overlap_candidate, slot_name, start_str, end_str))

                if not candidate_starts:
                    await log_line(f"[FILTER] ❌ Keine Zeitüberschneidung!")
                    await log_line(f"         Patient: {patient_start//60:02d}:{patient_start%60:02d} - {patient_end//60:02d}:{patient_end%60:02d}")
                    for start_str, end_str, slot_name in slot_ranges:
                        await log_line(f"         {slot_name}: {start_str} - {end_str}")
                    return (False, None)

                # Nimm die früheste passende Startzeit über beide Slots
                candidate_starts.sort(key=lambda x: x[0])
                overlap_start_time = candidate_starts[0][0]
                best_slot_name, best_start, best_end = candidate_starts[0][1], candidate_starts[0][2], candidate_starts[0][3]
                await log_line(f"[FILTER] ✅ Zeitüberschneidung vorhanden: Start bei {overlap_start_time} ({best_slot_name}: {best_start}-{best_end})")
        # Diagnose-Filter prüfen
        diag_include = filters.get("diagnosis", {}).get("include", "")
        diag_exclude = filters.get("diagnosis", {}).get("exclude", "")

        # Konvertiere zu Liste, falls String
        if isinstance(diag_include, str):
            diag_include = [x.strip() for x in diag_include.split(",") if x.strip()]
        if isinstance(diag_exclude, str):
            diag_exclude = [x.strip() for x in diag_exclude.split(",") if x.strip()]

        # Wenn Include-Filter gesetzt: mindestens einer muss vorkommen (mit Synonym-Match)
        if diag_include:
            # Für jeden Include-Filter: prüfe alle Synonyme (einfaches substring-Match wie Backup 2)
            match_found = False
            for diag_term in diag_include:
                synonyms = normalize_term(diag_term)
                if any(syn in case_text_lower for syn in synonyms):
                    match_found = True
                    break
            if not match_found:
                await log_line(f"[FILTER] ❌ Diagnose nicht in Include-Liste (auch Synonyme geprüft)")
                return (False, None)

        # Wenn Exclude-Filter gesetzt: keiner darf vorkommen (mit Synonym-Match)
        if diag_exclude:
            for diag_term in diag_exclude:
                synonyms = normalize_term(diag_term)
                if any(syn in case_text_lower for syn in synonyms):
                    await log_line(f"[FILTER] ❌ Diagnose in Exclude-Liste")
                    return (False, None)

        # Wunsch-Filter prüfen (AU, Rezept, Beratung)
        wish_include = filters.get("wishes", {}).get("include", "")
        wish_exclude = filters.get("wishes", {}).get("exclude", "")

        if isinstance(wish_include, str):
            wish_include = [x.strip() for x in wish_include.split(",") if x.strip()]
        if isinstance(wish_exclude, str):
            wish_exclude = [x.strip() for x in wish_exclude.split(",") if x.strip()]

        # Wenn Include-Filter gesetzt: mindestens einer muss vorkommen (mit Synonym-Match + Word Boundary)
        if wish_include:
            match_found = False
            for wish_term in wish_include:
                synonyms = normalize_term(wish_term)
                # Verwende Word-Boundary-Check für kurze Begriffe wie "AU"
                if any(word_boundary_match(case_text_lower, syn) for syn in synonyms):
                    match_found = True
                    break
            if not match_found:
                await log_line(f"[FILTER] ❌ Wunsch nicht in Include-Liste (auch Synonyme geprüft)")
                return (False, None)

        # Wenn Exclude-Filter gesetzt: keiner darf vorkommen (mit Synonym-Match + Word Boundary)
        if wish_exclude:
            for wish_term in wish_exclude:
                synonyms = normalize_term(wish_term)
                # Verwende Word-Boundary-Check für kurze Begriffe
                if any(word_boundary_match(case_text_lower, syn) for syn in synonyms):
                    await log_line(f"[FILTER] ❌ Wunsch in Exclude-Liste")
                    return (False, None)

        # Sprachen-Filter: VERBESSERT mit Synonymen
        lang_include = filters.get("patients", {}).get("language_include", "")
        lang_exclude = filters.get("patients", {}).get("language_exclude", "")

        if isinstance(lang_include, str):
            lang_include = [x.strip() for x in lang_include.split(",") if x.strip()]
        if isinstance(lang_exclude, str):
            lang_exclude = [x.strip() for x in lang_exclude.split(",") if x.strip()]

        # Normalisiere Sprachen-Begriffe für Matching
        # z.B. "English" → auch "englisch" matchen
        # Include prüfen mit normalize_term
        if lang_include:
            match_found = False
            for lang_term in lang_include:
                synonyms = normalize_term(lang_term)
                if any(syn in case_text_lower for syn in synonyms):
                    match_found = True
                    break
            if not match_found:
                await log_line(f"[FILTER] ❌ Sprache nicht in Include-Liste (auch Synonyme geprüft)")
                return (False, None)

        # Exclude prüfen mit normalize_term
        if lang_exclude:
            for lang_term in lang_exclude:
                synonyms = normalize_term(lang_term)
                if any(syn in case_text_lower for syn in synonyms):
                    await log_line(f"[FILTER] ❌ Sprache in Exclude-Liste")
                    return (False, None)

        # Alters-Filter
        age_min_raw = filters.get("patients", {}).get("age_min", "")
        age_max_raw = filters.get("patients", {}).get("age_max", "")
        age_min_val = int(age_min_raw) if str(age_min_raw).strip().isdigit() else None
        age_max_val = int(age_max_raw) if str(age_max_raw).strip().isdigit() else None

        age_val = None
        try:
            m_age = re.search(r"(\d{1,3})\s*(jahre|year|yrs|years|yo)", case_text_lower)
            if m_age:
                age_val = int(m_age.group(1))
        except Exception:
            age_val = None

        if (age_min_val is not None or age_max_val is not None) and age_val is None:
            await log_line("[FILTER] ❌ Alter nicht erkennbar, aber Altersgrenze gesetzt")
            return (False, None)

        if age_min_val is not None and age_val is not None and age_val < age_min_val:
            await log_line(f"[FILTER] ❌ Alter {age_val} unter Mindestalter {age_min_val}")
            return (False, None)
        if age_max_val is not None and age_val is not None and age_val > age_max_val:
            await log_line(f"[FILTER] ❌ Alter {age_val} über Maximalalter {age_max_val}")
            return (False, None)

        # Geschlechts-Filter
        gender = filters.get("patients", {}).get("gender", "").strip().lower()
        if gender:
            if gender == "m" and "männlich" not in case_text_lower and "male" not in case_text_lower:
                await log_line(f"[FILTER] ❌ Geschlecht stimmt nicht (erwartet: männlich)")
                return (False, None)
            if gender == "w" and "weiblich" not in case_text_lower and "female" not in case_text_lower:
                await log_line(f"[FILTER] ❌ Geschlecht stimmt nicht (erwartet: weiblich)")
                return (False, None)

        await log_line(f"[FILTER] ✅ Fall entspricht allen Filterkriterien")
        return (True, overlap_start_time)

    except Exception as e:
        await log_line(f"[FILTER] Fehler beim Prüfen der Filter: {e}")
        return (False, None)


def start_chrome_debug_mode():
    """
    Kompatibilitäts-Stub — wird nicht mehr benötigt.
    Chrome wird jetzt direkt von Playwright über launch_persistent_context gestartet.
    Kein Debug-Port, kein subprocess.
    """
    return None


def bring_chrome_to_foreground():
    """
    Bringt das Chrome-Fenster in den Vordergrund (Windows).
    Wichtig: Damit Playwright-Klicks auch registriert werden.
    """
    try:
        import ctypes
        import win32gui
        import win32con

        # Finde Chrome-Fenster
        hwnd = win32gui.FindWindow(None, "Google Chrome")
        if not hwnd:
            # Fallback: Suche Fenster mit "Chrome" im Namen
            def callback(hwnd, hwnds):
                if "Chrome" in win32gui.GetWindowText(hwnd):
                    hwnds.append(hwnd)
                return True
            hwnds = []
            win32gui.EnumWindows(callback, hwnds)
            if hwnds:
                hwnd = hwnds[0]

        if hwnd:
            # Fenster in den Vordergrund
            win32gui.SetForegroundWindow(hwnd)
            # Optional: Fenster maximieren falls minimiert
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
    except Exception as e:
        # Win32-Module möglicherweise nicht verfügbar - kein kritischer Fehler
        pass
    return False



async def handle_case(page, case_button, filters, overlap_time=None, case_element=None):
    """
    Klickt auf 'Anfrage übernehmen', wartet auf das Popup,
    setzt automatisch die Terminzeit via Scheduler und bestätigt.

    overlap_time: Wenn gesetzt, verwende diese Zeit statt Scheduler (aus Zeit-Overlap-Berechnung)
    case_element: Das Card-Element mit Patientendaten (wird gespeichert nach erfolgreichem Klick)
    """
    global patients_accepted

    try:
        await log_line("[SCAN] Anfrage gefunden – versuche zu übernehmen...")
        # Scroll & Klick robuster
        try:
            await page.bring_to_front()
            await page.wait_for_timeout(100)
        except Exception:
            pass
        try:
            await case_button.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass

        # Vor dem Klick evtl. offenes Overlay schließen (falls vorhanden)
        try:
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.15)
        except Exception:
            pass

        try:
            await case_button.click(timeout=5000)
        except Exception as e1:
            await log_line(f"[WARN] Normaler Klick fehlgeschlagen, versuche force=True: {e1}")
            try:
                await case_button.click(timeout=5000, force=True)
            except Exception as e2:
                await log_line(f"[WARN] Force-Klick fehlgeschlagen, versuche JS-Fallback: {e2}")
                try:
                    await case_button.evaluate("el => el.click()")
                except Exception as e3:
                    await log_line(f"[ERROR] Klick auf Karten-Button endgültig fehlgeschlagen: {e3}")
                    return False

        # Warte auf Dialog statt nur auf das Zeitfeld
        dialog_found = False
        try:
            dlg = page.get_by_role("dialog").first
            await dlg.wait_for(state="visible", timeout=10000)
            dialog_found = True
        except Exception:
            # Fallback: warte kurz und prüfe direkt auf Time-Input
            await page.wait_for_timeout(1000)

        if not dialog_found:
            try:
                if await page.locator("div[role='dialog']").count() > 0:
                    dialog_found = True
            except Exception:
                pass

        if dialog_found:
            await log_line("[POPUP] Dialog/Popup erkannt.")
        else:
            await log_line("[POPUP] ⚠️ Dialog nicht sicher erkennbar - prüfe trotzdem auf Zeitfeld/Fallbacks.")

        # WICHTIG: Nutze IMMER den Scheduler für korrekte Intervalle!
        # overlap_time wird als min_start_time übergeben (frühester erlaubter Start)
        target_date = get_target_date(filters)
        slot = next_available_slot(filters, date=target_date, min_start_time=overlap_time)

        if slot:
            if overlap_time:
                await log_line(f"[SCHEDULER] Slot zugewiesen: {slot} (Patientenwunsch ab {overlap_time})")
            else:
                await log_line(f"[SCHEDULER] Slot zugewiesen: {slot}")
        else:
            await log_line("[SCHEDULER] Keine freien Slots verfügbar.")

        if not slot:
            await log_line("[WARN] Keine freie Terminzeit mehr – überspringe Fall.")
            # Schließe Popup
            try:
                close_btn = page.get_by_role("button", name="Abbrechen").first
                if await close_btn.count():
                    await close_btn.click()
            except:
                pass
            return False

        # Zeitfeld im Dialog suchen (robust)
        time_input = None
        try:
            time_input = page.locator("div[role='dialog']").locator("input[type='time']").first
            if await time_input.count() == 0:
                time_input = page.locator("div[role='dialog']").get_by_role("textbox").first
                if await time_input.count() == 0:
                    time_input = None
        except Exception:
            time_input = None

        if not time_input:
            # Globaler Fallback
            ti = page.locator("input[type='time']").first
            if await ti.count():
                time_input = ti

        if not time_input:
            await log_line("[ERROR] Zeitfeld im Popup nicht gefunden.")
            return False

        # Zeit via React-kompatibler JS-Methode setzen
        # Direkte el.value-Zuweisung reicht bei React nicht — wir nutzen den nativen Setter
        react_set_js = f"""
(el => {{
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeSetter.call(el, '{slot}');
    el.dispatchEvent(new Event('input', {{bubbles: true}}));
    el.dispatchEvent(new Event('change', {{bubbles: true}}));
}})
"""
        accepted = False
        try:
            await time_input.click()
            await asyncio.sleep(0.2)
            await time_input.evaluate(react_set_js)
            await asyncio.sleep(0.4)
            val = await time_input.input_value()
            if val and val[:5] == slot[:5]:
                accepted = True
                await log_line(f"[TIME] ✅ Zeit gesetzt (React-JS): {slot}")
            else:
                await log_line(f"[TIME] ⚠️ React-JS: UI zeigt '{val}' statt '{slot}' – versuche fill()")
        except Exception as e:
            await log_line(f"[TIME] ⚠️ React-JS fehlgeschlagen: {e}")

        if not accepted:
            # Fallback 1: Playwright fill()
            try:
                await time_input.fill(slot)
                await asyncio.sleep(0.3)
                val = await time_input.input_value()
                if val and val[:5] == slot[:5]:
                    accepted = True
                    await log_line(f"[TIME] ✅ Zeit gesetzt (fill): {slot}")
                else:
                    await log_line(f"[TIME] ⚠️ fill(): UI zeigt '{val}'")
            except Exception as e2:
                await log_line(f"[TIME] ⚠️ fill() fehlgeschlagen: {e2}")

        if not accepted:
            # Fallback 2: Tastatureingabe (Ctrl+A dann tippen)
            try:
                await time_input.click()
                await asyncio.sleep(0.1)
                await time_input.press("Control+a")
                await time_input.type(slot.replace(":", ""))
                await asyncio.sleep(0.3)
                val = await time_input.input_value()
                if val and val[:5] == slot[:5]:
                    accepted = True
                    await log_line(f"[TIME] ✅ Zeit gesetzt (keyboard): {slot}")
                else:
                    await log_line(f"[TIME] ⚠️ keyboard: UI zeigt '{val}'")
            except Exception as e3:
                await log_line(f"[TIME] ⚠️ keyboard-Eingabe fehlgeschlagen: {e3}")

        if not accepted:
            await log_line(f"[ERROR] Keine Methode konnte Zeit '{slot}' setzen – überspringe Fall.")
            try:
                close_btn = page.get_by_role("button", name="Abbrechen").first
                if await close_btn.count():
                    await close_btn.click()
            except Exception:
                pass
            return False

        # 'Übernehmen'-Button im Dialog finden und klicken
        pickup = None
        try:
            import re as _re
            dlg = page.get_by_role("dialog").first
            pickup = dlg.get_by_role("button", name=_re.compile(r"Übernehmen|Uebernehmen", _re.I)).last
            if await pickup.count() == 0:
                pickup = None
        except Exception:
            pickup = None

        if not pickup:
            # Fallbacks
            pickup = page.locator("div[role='dialog'] button:has-text('Übernehmen')").last
            if await pickup.count() == 0:
                pickup = page.locator("button:has-text('Übernehmen')").last

        if await pickup.count() == 0:
            await log_line("[ERROR] 'Übernehmen'-Button nicht gefunden!")
            return False

        # Sicherstellen, dass Button klickbar ist
        try:
            await pickup.wait_for(state="visible", timeout=5000)
            if await pickup.is_disabled():
                await log_line("[WARN] 'Übernehmen'-Button ist deaktiviert – Zeit evtl. ungültig")
                return False
            try:
                await pickup.click(timeout=5000)
            except Exception as e1:
                await log_line(f"[WARN] Normaler Klick auf 'Übernehmen' fehlgeschlagen, versuche force=True: {e1}")
                try:
                    await pickup.click(timeout=5000, force=True)
                except Exception as e2:
                    await log_line(f"[WARN] Force-Klick auf 'Übernehmen' fehlgeschlagen, versuche JS-Fallback: {e2}")
                    try:
                        await pickup.evaluate("el => el.click()")
                    except Exception as e3:
                        await log_line(f"[ERROR] Klick auf 'Übernehmen' endgültig fehlgeschlagen: {e3}")
                        return False
        except Exception as e:
            await log_line(f"[ERROR] Klick auf 'Übernehmen' fehlgeschlagen: {e}")
            return False

        # ── FIX: Slot sofort als belegt bestätigen (verhindert Doppelbelegung) ──
        try:
            from core_scheduler import confirm_slot
            confirm_slot(slot, date=target_date)
            await log_line(f"[SCHEDULER] ✅ Slot {slot} als belegt gespeichert.")
        except Exception as cs_err:
            await log_line(f"[SCHEDULER] ⚠️ confirm_slot fehlgeschlagen (nicht kritisch): {cs_err}")

        # Counter erhöhen
        patients_accepted += 1
        await log_line(f"[OK] Anfrage übernommen – Termin {slot} gesetzt.")
        await log_line(f"[INFO] 📊 Patienten übernommen: {patients_accepted}")

        # NEEU: Speichere Patient-Daten in scheduled_patients.json
        if case_element:
            try:
                from scheduled_patients import add_patient
                from datetime import datetime, timedelta

                # Extrahiere Patient-Daten aus case_element
                parent = await case_element.evaluate_handle('el => el.parentElement')
                case_text = await parent.evaluate('el => el.innerText')
                case_text_lower = normalize_text(case_text)

                # Parse TATSÄCHLICHE Diagnose aus dem Fall
                # SIMPEL: Die Diagnose ist die ERSTE Zeile nach GKV/VIDEO
                diagnosis = "(unbekannt)"

                lines = case_text.split("\n")
                skip_next = False

                for line in lines:
                    line_lower = normalize_text(line)

                    # Springe GKV/VIDEO über
                    if line_lower in ["gkv", "video"]:
                        skip_next = True
                        continue

                    # Nach GKV/VIDEO: nimm die erste nicht-leere, nicht-Zahl-Zeile
                    if skip_next and line and len(line) > 2:
                        # Überspringe reine Zahlen/Alter
                        if not line.replace(",", "").replace(" ", "").replace(".", "").replace("-", "").replace("(", "").replace(")", "").replace("jahre", "").replace("year", "").replace("yrs", "").isdigit():
                            diagnosis = line.title()
                            break

                # Parse TATSÄCHLICHE Wünsche aus dem Fall
                wishes = "(keine)"
                wishes_keywords = ["au", "arbeitsunfähigkeit", "rezept", "beratung", "video", "telemedizin"]
                found_wishes = []
                for keyword in wishes_keywords:
                    if keyword in case_text_lower:
                        found_wishes.append(keyword.upper() if keyword != "au" else "AU")
                if found_wishes:
                    wishes = ", ".join(found_wishes[:2])  # Max 2 Wünsche

                # Parse Alter
                import re
                age = "(egal)"
                m_age = re.search(r"(\d{1,3})\s*(jahre|years|yrs|year|yo)", case_text_lower)
                if m_age:
                    age = m_age.group(1)

                # Parse Geschlecht
                gender = ""
                if "männlich" in case_text_lower or "male" in case_text_lower:
                    gender = "männlich"
                elif "weiblich" in case_text_lower or "female" in case_text_lower:
                    gender = "weiblich"
                elif "divers" in case_text_lower or "diverse" in case_text_lower:
                    gender = "divers"
                else:
                    gender = "(egal)"

                # Bestimme das richtige Datum basierend auf dem Filter
                from datetime import datetime, timedelta
                day_window = filters.get("time_filter", {}).get("day_window", "heute")
                if day_window == "morgen":
                    # Scanner läuft auf Morgen-Seite → speichere für morgen
                    target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                elif day_window == "später":
                    # Scanner läuft auf Später-Seite → speichere für übermorgen
                    target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
                else:
                    # Scanner läuft auf Heute-Seite → speichere für heute
                    target_date = datetime.now().strftime("%Y-%m-%d")

                # Speichere mit richtigem Datum
                add_patient(slot, diagnosis, wishes, gender, age, date=target_date)
                await log_line(f"[PATIENT] ✅ Patientendaten gespeichert ({target_date}): {slot} | {diagnosis} | {gender} | {age}J")
                await log_line("[PATIENT] GUI-Kalender-Update nach Import")
            except Exception as e:
                await log_line(f"[PATIENT] ⚠️ Fehler beim Speichern: {e}")

        await asyncio.sleep(1)
        return True

    except PlaywrightTimeoutError:
        await log_line("[ERROR] Timeout beim Terminieren.")
        return False
    except Exception as e:
        await log_line(f"[ERROR] Unerwarteter Fehler beim Klickvorgang: {e}")
        return False


async def ensure_teleclinic_requests_page(page, tab_num: int, page_num: int = 1, retries: int = 2) -> bool:
    """Navigiert robust zur Requests-Seite und toleriert langsame Netz-/SPA-Zustände."""
    target_url = f"https://med.teleclinic.com/requests?tab={tab_num}&page={page_num}"

    for attempt in range(1, retries + 1):
        try:
            current_url = page.url or ""
            if "med.teleclinic.com/requests" in current_url and f"tab={tab_num}" in current_url and f"page={page_num}" in current_url:
                await log_line(f"[INFO] Bereits auf Zielseite: {target_url}")
                return True

            await log_line(f"[INFO] Navigiere zu {target_url}... (Versuch {attempt}/{retries})")
            await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)

            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                await log_line("[INFO] Seite noch aktiv/lädt weiter - fahre mit DOM-Check fort")

            await asyncio.sleep(2)

            final_url = page.url or ""
            if "med.teleclinic.com/requests" in final_url and f"tab={tab_num}" in final_url:
                return True

            if "login" in final_url or "auth" in final_url or "signin" in final_url:
                await log_line(f"[WARN] Teleclinic verlangt Login/Bestätigung: {final_url}")
                await log_line("[INFO] ⏳ Bitte jetzt im Chrome-Fenster einloggen! Warte bis zu 120 Sekunden...")
                # Warte bis zu 120 Sekunden und prüfe wiederholt, ob Login abgeschlossen
                for wait_sec in range(0, 120, 5):
                    await asyncio.sleep(5)
                    check_url = page.url or ""
                    if "med.teleclinic.com/requests" in check_url or "med.teleclinic.com" in check_url and "auth" not in check_url and "login" not in check_url:
                        await log_line(f"[INFO] ✅ Login erkannt! Seite: {check_url}")
                        # Nach Login nochmal zur Zielseite navigieren
                        try:
                            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                            await asyncio.sleep(2)
                        except Exception:
                            pass
                        return True
                    if wait_sec % 15 == 0 and wait_sec > 0:
                        await log_line(f"[INFO] ⏳ Warte auf Login... ({120 - wait_sec}s verbleibend)")
                await log_line("[ERROR] Login-Timeout nach 120 Sekunden - bitte manuell einloggen und Bot neu starten")
                return False

            await log_line(f"[WARN] Unerwartete Zielseite nach Navigation: {final_url}")
        except PlaywrightTimeoutError as e:
            await log_line(f"[WARN] Navigation-Timeout zu {target_url}: {e}")
        except Exception as e:
            await log_line(f"[WARN] Navigation fehlgeschlagen zu {target_url}: {e}")

        try:
            await page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
        except Exception:
            pass

    await log_line(f"[ERROR] Requests-Seite konnte nicht stabil geöffnet werden: {target_url}")
    return False


async def get_preferred_teleclinic_page(context):
    """
    Finde robust den richtigen Teleclinic-Tab statt blind context.pages[0] zu verwenden.
    Priorität:
    1. requests-Tab
    2. myappointments-Tab
    3. irgendein med.teleclinic.com-Tab
    4. Fallback: erste vorhandene Seite oder neue Seite
    """
    pages = list(context.pages)

    def url_of(p):
        try:
            return (p.url or "").lower()
        except Exception:
            return ""

    requests_pages = [p for p in pages if "med.teleclinic.com/requests" in url_of(p)]
    myappointments_pages = [p for p in pages if "med.teleclinic.com/myappointments" in url_of(p)]
    teleclinic_pages = [p for p in pages if "med.teleclinic.com" in url_of(p)]

    if requests_pages:
        page = requests_pages[0]
        await log_line(f"[TAB] Nutze vorhandenen Requests-Tab: {page.url}")
    elif myappointments_pages:
        page = myappointments_pages[0]
        await log_line(f"[TAB] Nutze vorhandenen MyAppointments-Tab: {page.url}")
    elif teleclinic_pages:
        page = teleclinic_pages[0]
        await log_line(f"[TAB] Nutze vorhandenen Teleclinic-Tab: {page.url}")
    elif pages:
        page = pages[0]
        await log_line(f"[TAB] Kein Teleclinic-Tab gefunden, nutze erste offene Seite: {page.url}")
    else:
        page = await context.new_page()
        await log_line("[TAB] Kein offener Tab gefunden, neue Seite erstellt")

    try:
        await page.bring_to_front()
        await page.wait_for_timeout(150)
        await log_line("[TAB] Tab in den Vordergrund geholt")
    except Exception as e:
        await log_line(f"[TAB] Vordergrund-Aktivierung nicht möglich (nicht kritisch): {e}")

    return page


def build_slot_filters(slot_data: dict, day_window: str, slot_num: int) -> dict:
    """
    Konvertiert Slot-Daten (neues GUI-Format) in das bisherige Filterformat,
    damit check_case_matches_filters() unverändert weiterverwendet werden kann.
    """
    if not slot_data:
        slot_data = {}

    return {
        "time_filter": {
            "day_window": day_window,
            "treatment_start": slot_data.get("time_start", ""),
            "treatment_end": slot_data.get("time_end", ""),
            # Für die slot-spezifische Prüfung bleibt das zweite Zeitfenster hier leer.
            # Das Routing Slot 1 / Slot 2 passiert bereits in click_loop().
            "treatment_start_2": "",
            "treatment_end_2": "",
        },
        "runtime": {
            "max_patients": slot_data.get("max_patients", 5),
            "interval_minutes": slot_data.get("interval_minutes", 5),
        },
        "patients": {
            "gender": slot_data.get("gender", ""),
            "age_min": slot_data.get("age_min", ""),
            "age_max": slot_data.get("age_max", ""),
            "language_include": [x.strip() for x in str(slot_data.get("language_include", "")).split(",") if x.strip()],
            "language_exclude": [x.strip() for x in str(slot_data.get("language_exclude", "")).split(",") if x.strip()],
        },
        "diagnosis": {
            "include": slot_data.get("diagnosis_include", ""),
            "exclude": slot_data.get("diagnosis_exclude", ""),
        },
        "wishes": {
            "include": slot_data.get("wishes_include", ""),
            "exclude": slot_data.get("wishes_exclude", ""),
        },
        "loop": {},
    }


async def check_and_update_day_window(filters, last_midnight_check=None):
    """
    Prüft ob Mitternacht überschritten wurde und aktualisiert day_window Filter.
    Returns: (updated_filters, last_midnight_check_time)
    """
    now = datetime.now()

    if last_midnight_check:
        time_since_check = (now - last_midnight_check).total_seconds()
        if time_since_check < 30:
            return (filters, last_midnight_check)

    current_time = now.time()
    if current_time.hour < 4 and last_midnight_check is None:
        old_day_window = filters.get("time_filter", {}).get("day_window", "heute")
        if old_day_window == "morgen":
            new_day_window = "heute"
            await log_line(f"[MIDNIGHT] 🌙 Mitternacht überschritten! Wechsle Filter: {old_day_window} → {new_day_window}")
            filters["time_filter"]["day_window"] = new_day_window
        elif old_day_window == "später":
            new_day_window = "morgen"
            await log_line(f"[MIDNIGHT] 🌙 Mitternacht überschritten! Wechsle Filter: {old_day_window} → {new_day_window}")
            filters["time_filter"]["day_window"] = new_day_window

    return (filters, now)


def get_target_date_from_filters(filters: dict) -> str:
    """Bestimmt das Zieldatum passend zum day_window-Filter (lokale Hilfsfunktion)."""
    day_window = normalize_text(filters.get("time_filter", {}).get("day_window", "heute"))
    now = datetime.now()
    if day_window == "morgen":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if day_window == "später":
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


async def import_existing_appointments(page, filters) -> int:
    """
    Liest bereits terminierte Patienten von 'Meine offene Fälle' aus
    und markiert deren Uhrzeiten in scheduled_slots.json als belegt.
    Returns: Anzahl der importierten Zeitslots
    """
    day_window = normalize_text(filters.get("time_filter", {}).get("day_window", "heute"))
    if day_window == "morgen":
        tab = 1
    else:
        tab = 0

    target_date = get_target_date_from_filters(filters)
    imported_times = {}  # dict: time -> card-data

    await log_line("=" * 70)
    await log_line(f"[IMPORT] 📋 Lese bestehende Termine aus 'Meine offene Fälle' (Tab={tab})...")

    max_pages = 5
    for page_num in range(1, max_pages + 1):
        url = f"https://med.teleclinic.com/myappointments?tab={tab}&page={page_num}"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            await asyncio.sleep(3)

            current_url = page.url or ""
            if "myappointments" not in current_url:
                await log_line(f"[IMPORT] ⚠️ Umgeleitet auf {current_url} - Login erforderlich?")
                break

            await log_line(f"[IMPORT] 🔍 Scanneseite {page_num} nach Terminen...")


            try:
                cards_raw = await page.evaluate("""() => {
    const results = [];
    const timeEls = Array.from(document.querySelectorAll('*')).filter(el => {
        const t = (el.innerText || '').trim();
        return /^\\d{1,2}:\\d{2}(\\s*Uhr)?$/.test(t) && el.children.length === 0;
    });
    const cards = new Set();
    for (const tel of timeEls) {
        let el = tel.parentElement;
        for (let i = 0; i < 6 && el; i++) {
            const txt = (el.innerText || '').trim();
            if (txt.length > 30 && /\\d{1,2}:\\d{2}/.test(txt)) {
                cards.add(el);
                break;
            }
            el = el.parentElement;
        }
    }
    if (cards.size === 0) {
        const selectors = [
            '[data-testid*="appointment"]', '[data-testid*="treatment"]',
            '[class*="appointment"]', '[class*="treatment"]',
            '[class*="case"]', '[class*="card"]', 'li', 'article'
        ];
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) {
                const text = (el.innerText || '').trim();
                if (/\\d{1,2}:\\d{2}/.test(text) && text.length > 15)
                    cards.add(el);
            }
            if (cards.size > 0) break;
        }
    }
    const cardArr = Array.from(cards);
    const outer = cardArr.filter(el =>
        !cardArr.some(other => other !== el && other.contains(el))
    );
    for (const card of outer) {
        const text = (card.innerText || '').trim();
        const timeM = text.match(/(\\d{1,2}):(\\d{2})(?:\\s*Uhr)?/);
        if (!timeM) continue;
        const time_str = timeM[1].padStart(2,'0') + ':' + timeM[2];
        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 1);
        let diagnosis = '', wishes = '', gender = '', age = '';
        const skip = [
            /^\\d{1,2}:\\d{2}(\\s*Uhr)?$/,
            /^(video|gkv|pkv|privat|selbstzahler|termin stornieren|zum fall|mehr infos|direktanfragen)$/i,
            /^\\d{1,2}\\.\\d{1,2}(\\.\\d{2,4})?$/,
            /^(morgen|heute|später)/i,
            /^\\d+\\s*km$/i,
            /^\\d+\\s*%/i
        ];
        let diagFound = false;
        for (const line of lines) {
            if (skip.some(p => p.test(line.trim()))) continue;
            const genderAgeCombo = line.match(/(männlich|weiblich|divers|male|female)[,\\s]+(\\d{1,3})\\s*(J\\.?|Jahre?)?/i);
            if (genderAgeCombo) {
                if (!gender) gender = genderAgeCombo[1].trim();
                if (!age) age = genderAgeCombo[2];
                continue;
            }
            if (!gender && /(männlich|weiblich|divers|male|female)/i.test(line)) {
                gender = line.trim(); continue;
            }
            const m = line.match(/(\\d{1,3})\\s*(J\\.?|Jahre?)/i);
            if (!age && m) { age = m[1]; continue; }
            // Wunsch: nur wenn die Zeile AUSSCHLIESSLICH ein Wunsch-Keyword ist (kein Diagnose-Text daneben)
            if (!wishes && /^(AU|Rezept|Beratung|Krankschreib|Attest|Überweisung)(\\s*[,&+]\\s*(AU|Rezept|Beratung|Krankschreib|Attest|Überweisung))*$/i.test(line.trim())) {
                wishes = line.trim(); continue;
            }
            // Zeilen wie "AU, Kopfschmerzen" → Wunsch=AU, Diagnose=Kopfschmerzen
            const auMix = line.match(/^(AU|Rezept|Attest|Krankschreib)[,\\s]+(.+)$/i);
            if (auMix && !diagFound) {
                if (!wishes) wishes = auMix[1].trim();
                diagnosis = auMix[2].trim(); diagFound = true; continue;
            }
            if (!diagFound && line.length >= 3 &&
                !/(männlich|weiblich|male|female|divers|Jahre|\\d+\\s*J\\.?)/i.test(line)) {
                diagnosis = line.trim(); diagFound = true; continue;
            }
        }
        results.push({ time: time_str, diagnosis, wishes, gender, age });
    }
    return results;
}""")
            except Exception as eval_err:
                await log_line(f"[IMPORT] ⚠️ DOM-Auswertung fehlgeschlagen: {eval_err}")
                cards_raw = []

            seen_times = {}
            for card in cards_raw:
                t = card.get("time", "")
                if t and t not in seen_times:
                    seen_times[t] = card
            time_matches = list(seen_times.keys())

            if not time_matches:
                await log_line(f"[IMPORT] Seite {page_num}: Keine Termine gefunden - Ende der Seiten.")
                break

            for t in time_matches:
                imported_times[t] = seen_times[t]
            await log_line(f"[IMPORT] Seite {page_num}: {len(time_matches)} Termine gefunden")

            has_more = await page.evaluate("""() => {
                const links = document.querySelectorAll('a[href*="page="]');
                return links.length > 0;
            }""")
            if not has_more:
                break

        except PlaywrightTimeoutError:
            await log_line(f"[IMPORT] ⚠️ Timeout bei Seite {page_num} - überspringe")
            break
        except Exception as e:
            await log_line(f"[IMPORT] ⚠️ Fehler bei Seite {page_num}: {e}")
            break

    if imported_times:
        imported_time_set = set(imported_times.keys())
        slots = load_slots()
        existing = set(slots.get(target_date, []))
        merged = sorted(existing | imported_time_set)
        slots[target_date] = merged
        save_slots(slots)

        try:
            from scheduled_patients import add_imported_appointment
            for t in sorted(imported_time_set):
                card = imported_times[t]
                add_imported_appointment(
                    t, date=target_date,
                    diagnosis=card.get("diagnosis") or "Extern terminiert",
                    wishes=card.get("wishes") or "",
                    gender=card.get("gender") or "",
                    age=card.get("age") or ""
                )
        except Exception as patient_import_err:
            await log_line(f"[IMPORT] ⚠️ Kalender-Spiegelung fehlgeschlagen: {patient_import_err}")

        sorted_imports = sorted(imported_time_set)
        await log_line(f"[IMPORT] ✅ {len(imported_time_set)} bestehende Termine importiert für {target_date}:")
        await log_line(f"[IMPORT]    Zeiten: {', '.join(sorted_imports)}")
    else:
        await log_line(f"[IMPORT] ℹ️ Keine bestehenden Termine für {target_date} gefunden.")

    await log_line("=" * 70)
    return len(imported_times)


async def click_loop(filters):
    """Durchsuche regelmäßig die Seite nach übernehmbaren Fällen."""
    global patients_accepted
    # Reset am Start eines jeden Laufs
    patients_accepted = 0
    await log_line("[RESET] Patientenanzahl auf 0 zurückgesetzt.")

    scan_interval = int(filters.get("loop", {}).get("scan_interval_sec", 10))
    max_pages = int(filters.get("loop", {}).get("max_pages", 5))

    day_window_global = filters.get("time_filter", {}).get("day_window", "heute")

    # ── Slot-Konfiguration ermitteln ──────────────────────────────────────────
    # Neues Format (slot1 / slot2_enabled / slot2)?
    if "slot1" in filters:
        slot1_data = filters["slot1"]
        slot2_enabled = filters.get("slot2_enabled", False)
        slot2_data = filters.get("slot2", {}) if slot2_enabled else None
    else:
        # Altes Format: Kompatibilitäts-Fallback → alles in Slot 1
        slot1_data = {
            "time_start": filters.get("time_filter", {}).get("treatment_start", ""),
            "time_end": filters.get("time_filter", {}).get("treatment_end", ""),
            "max_patients": filters.get("runtime", {}).get("max_patients", 5),
            "interval_minutes": filters.get("runtime", {}).get("interval_minutes", 5),
            "diagnosis_include": filters.get("diagnosis", {}).get("include", ""),
            "diagnosis_exclude": filters.get("diagnosis", {}).get("exclude", ""),
            "wishes_include": filters.get("wishes", {}).get("include", ""),
            "wishes_exclude": filters.get("wishes", {}).get("exclude", ""),
            "language_include": ",".join(filters.get("patients", {}).get("language_include", [])),
            "language_exclude": ",".join(filters.get("patients", {}).get("language_exclude", [])),
            "age_min": str(filters.get("patients", {}).get("age_min", "")),
            "age_max": str(filters.get("patients", {}).get("age_max", "")),
            "gender": filters.get("patients", {}).get("gender", "")
        }
        slot2_enabled = False
        slot2_data = None

    # Filter-Dicts für check_case_matches_filters() aufbauen
    slot1_filters = build_slot_filters(slot1_data, day_window_global, 1)
    slot2_filters = build_slot_filters(slot2_data, day_window_global, 2) if slot2_data else None

    # Pro-Slot-Limits (robust gegen leere oder ungültige Werte)
    try:
        slot1_max = int(slot1_data.get("max_patients") or 5)
        if slot1_max <= 0:
            slot1_max = 5
    except (ValueError, TypeError):
        slot1_max = 5

    if slot2_data:
        try:
            slot2_max = int(slot2_data.get("max_patients") or 5)
            if slot2_max <= 0:
                slot2_max = 5
        except (ValueError, TypeError):
            slot2_max = 5
    else:
        slot2_max = 0

    # Pro-Slot-Zähler
    slot1_accepted = 0
    slot2_accepted = 0

    await log_line("=" * 70)
    await log_line(f"[INFO] 🕐 SLOT 1: {slot1_data.get('time_start','?')} - {slot1_data.get('time_end','?')} | Max: {slot1_max}")
    if slot2_enabled and slot2_data:
        await log_line(f"[INFO] 🕑 SLOT 2: {slot2_data.get('time_start','?')} - {slot2_data.get('time_end','?')} | Max: {slot2_max}")
    else:
        await log_line("[INFO] SLOT 2: deaktiviert")
    await log_line(f"[INFO] Scan-Intervall: {scan_interval} Sekunden | Max. Seiten: {max_pages}")
    await log_line("=" * 70)

    # Für Overnight-Scans: Merke uns die letzte Mitternacht-Prüfung
    last_midnight_check = None

    async with async_playwright() as p:
        try:
            # Starte Chrome direkt über Playwright — kein Debug-Port nötig.
            # launch_persistent_context nutzt das vorhandene Chrome-Profil (inkl. Login-Session).
            user_data_dir = str(ROOT / "chrome_profile")
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                channel="chrome",
                headless=False,
                args=[
                    "--lang=de",                                   # 24h-Format erzwingen
                    "--disable-blink-features=AutomationControlled",
                ],
                locale="de-DE",
            )
            await log_line("[START] Chrome gestartet (Profil: chrome_profile).")

            pages = list(context.pages)
            page = next(
                (pg for pg in pages if "med.teleclinic.com" in (pg.url or "")),
                pages[0] if pages else await context.new_page()
            )
            await page.bring_to_front()

            # Navigiere zu Teleclinic falls nicht schon dort
            current_url = page.url or ""
            if "med.teleclinic.com" not in current_url:
                await log_line("[INFO] Öffne Teleclinic-Startseite...")
                try:
                    await page.goto("https://med.teleclinic.com/", wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    current_url = page.url or ""
                except Exception:
                    pass

            await log_line(f"[INFO] Aktuelle URL: {current_url}")

            # ── LOGIN-VERIFIZIERUNG ──────────────────────────────────────────
            # Schnelle Prüfung: Wenn bereits bei med.teleclinic.com OHNE auth/login-Seiten,
            # dann ist der User eingeloggt → springe die Wartezeit!
            is_already_logged_in = (
                current_url and
                "med.teleclinic.com" in current_url and
                "auth" not in current_url and
                "login" not in current_url
            )

            if not is_already_logged_in:
                await log_line("[LOGIN] ⏳ Chrome ist noch nicht bei Teleclinic eingeloggt.")
                await log_line("[LOGIN] ⏳ Bitte jetzt im Chrome-Fenster einloggen! Warte bis zu 120 Sekunden...")
                login_ok = False
                for wait_sec in range(0, 120, 5):
                    await asyncio.sleep(5)
                    try:
                        check_url = page.url or ""
                        if "med.teleclinic.com" in check_url and "auth" not in check_url and "login" not in check_url:
                            await log_line(f"[LOGIN] ✅ Login erkannt! Seite: {check_url}")
                            login_ok = True
                            break
                        if wait_sec % 15 == 0 and wait_sec > 0:
                            await log_line(f"[LOGIN] ⏳ Warte auf Login... ({120 - wait_sec}s verbleibend)")
                    except Exception:
                        pass
                if not login_ok:
                    await log_line("[LOGIN] ❌ Login-Timeout nach 120 Sekunden.")
                    await log_line("[LOGIN] Bitte manuell einloggen und Bot neu starten.")
                    return
            else:
                await log_line("[LOGIN] ✅ Bereits eingeloggt! Springe Wartezeit.")

            # HYBRID-ANSATZ: URL-Navigation mit Validierung
            day_window = filters.get("time_filter", {}).get("day_window", "heute")
            tab_num = get_tab_number(day_window)
            day_name = "Heute" if tab_num == 0 else ("Morgen" if tab_num == 1 else "Später")

            await log_line(f"[INFO] 🗓️ Tag-Filter: {day_name} (Methode: URL tab={tab_num} + Validierung)")
            await log_line(f"[INFO] 🌙 Overnight-Scanning aktiviert: Bei Mitternacht wird Filter automatisch aktualisiert")

            # ── IMPORT: Bestehende Termine IMMER frisch aus Teleclinic laden ──
            # Wichtig: Immer resetten + neu importieren, damit keine veralteten
            # Slots aus dem letzten Lauf den Scheduler blockieren.
            target_date = get_target_date_from_filters(filters)
            await log_line(f"[IMPORT] 🔄 Starte frischen Import für {target_date}...")

            reset_slots_for_date(target_date)
            try:
                from scheduled_patients import reset_patients_for_date as _reset_patients
                _reset_patients(target_date, keep_imported=False)
            except Exception as rpe:
                await log_line(f"[IMPORT] ⚠️ Reset fehlgeschlagen (nicht kritisch): {rpe}")

            try:
                imported_count = await import_existing_appointments(page, filters)
                if imported_count > 0:
                    await log_line(f"[IMPORT] 📋 {imported_count} bestehende Termine als belegt markiert.")
                    from core_scheduler import load_slots as _load_slots
                    _slots = _load_slots()
                    _today = _slots.get(target_date, [])
                    if _today:
                        await log_line(f"[IMPORT] 📋 Belegte Slots: {', '.join(sorted(_today))}")
                else:
                    await log_line(f"[IMPORT] ℹ️ Keine bestehenden Termine gefunden — starte mit leeren Slots.")
                await log_line("[PATIENT] GUI-Kalender-Update nach Import")
            except Exception as e:
                await log_line(f"[IMPORT] ⚠️ Import fehlgeschlagen (Scan läuft trotzdem): {e}")

            # Wenn nicht auf der richtigen Seite ODER falscher Tab, navigiere dorthin
            # Nach Import von myappointments muss immer navigiert werden
            current_url = page.url or ""  # Aktualisiere nach Import
            needs_navigation = (
                "med.teleclinic.com/requests" not in current_url or
                f"tab={tab_num}" not in current_url
            )

            if needs_navigation:
                navigation_ok = await ensure_teleclinic_requests_page(page, tab_num, page_num=1)
                if not navigation_ok:
                    await log_line("[WARN] Erster Navigationsversuch fehlgeschlagen - warte 10 Sekunden und versuche erneut...")
                    await asyncio.sleep(10)
                    navigation_ok = await ensure_teleclinic_requests_page(page, tab_num, page_num=1)
                    if not navigation_ok:
                        await log_line("[ERROR] Requests-Seite nicht erreichbar oder Login nicht mehr aktiv.")
                        return

            # VALIDIERUNG + FALLBACK: Prüfe ob Tag-Filter wirklich gesetzt ist
            validation_ok = await validate_and_fix_day_filter(page, day_window)
            if not validation_ok:
                await log_line("[WARN] Tag-Filter konnte nicht verifiziert werden - fahre trotzdem fort")

            await log_line("[START] Bereit zum Scannen. Los geht's!")
            await log_line("=" * 70)

        except Exception as e:
            await log_line(f"[ERROR] Konnte Chrome nicht starten oder verbinden: {e}")
            await log_line("[INFO] Bitte prüfen: Ist Google Chrome installiert? Ist das Profil 'chrome_profile' vorhanden?")
            return

        loop_counter = 0  # Zähler für Re-Import-Intervall
        while True:
            try:
                # 🌙 OVERNIGHT-FEATURE: Prüfe ob Mitternacht überschritten wurde
                filters, last_midnight_check = await check_and_update_day_window(filters, last_midnight_check)

                # Stelle pro Loop sicher, dass wir weiter mit dem richtigen Teleclinic-Tab arbeiten
                page = await get_preferred_teleclinic_page(context)

                # 🪟 WICHTIG: Chrome-Fenster in den Vordergrund für zuverlässige Klicks
                bring_chrome_to_foreground()
                await page.bring_to_front()
                await asyncio.sleep(0.2)

                # HYBRID-ANSATZ: Bestimme Tab und navigiere
                day_window = filters.get("time_filter", {}).get("day_window", "heute")
                tab_num = get_tab_number(day_window)

                # 📋 RE-IMPORT: Alle 5 Loops Slots neu einlesen
                # Nur scheduled_slots.json resetten + neu befüllen
                # scheduled_patients.json NICHT anfassen — verhindert kurzes Verschwinden im GUI
                loop_counter += 1
                if loop_counter % 5 == 0:
                    try:
                        _reimport_date = get_target_date_from_filters(filters)
                        reset_slots_for_date(_reimport_date)
                        reimport_count = await import_existing_appointments(page, filters)
                        if reimport_count > 0:
                            await log_line(f"[IMPORT-LOOP] 📋 {reimport_count} Slots aktualisiert (Re-Import #{loop_counter})")
                        await log_line("[PATIENT] GUI-Kalender-Update nach Import")
                        await ensure_teleclinic_requests_page(page, tab_num, page_num=1)
                    except Exception as reimport_err:
                        await log_line(f"[IMPORT-LOOP] ⚠️ Re-Import fehlgeschlagen: {reimport_err}")
                        try:
                            await ensure_teleclinic_requests_page(page, tab_num, page_num=1)
                        except Exception:
                            pass

                # Durchsuche alle Seiten
                total_found = 0
                for page_num in range(1, max_pages + 1):
                    navigation_ok = await ensure_teleclinic_requests_page(page, tab_num, page_num=page_num)
                    if not navigation_ok:
                        await log_line("[WARN] Seite konnte in diesem Durchlauf nicht geladen werden - neuer Versuch im nächsten Loop")
                        break

                    # NUR bei erster Seite: Validierung durchführen
                    if page_num == 1:
                        validation_ok = await validate_and_fix_day_filter(page, day_window)
                        if not validation_ok:
                            await log_line("[WARN] Datumsfilter-Validierung fehlgeschlagen - Scan läuft trotzdem")

                    await log_line(f"[SCAN] Scanne Seite {page_num} (tab={tab_num})...")

                    # Finde alle Karten (KORRIGIERT: verwende data-testid statt Buttons)
                    cards = await page.query_selector_all("[data-testid='link-treatment-view']")
                    await log_line(f"[SCAN] Seite {page_num}: {len(cards)} übernehmbare Anfragen gefunden.")
                    total_found += len(cards)

                    for idx, card in enumerate(cards):
                        # ── Stop-Bedingung: beide Slots voll ──────────────────────
                        slot1_full = slot1_accepted >= slot1_max
                        slot2_full = (not slot2_enabled) or (slot2_accepted >= slot2_max)

                        if slot1_full and slot2_full:
                            await log_line("=" * 70)
                            await log_line(f"[STOP] 🎯 Alle Slots voll: Slot 1 {slot1_accepted}/{slot1_max} | Slot 2 {slot2_accepted}/{slot2_max}")
                            await log_line("[STOP] Bot wird beendet. Ziel erreicht!")
                            await log_line("=" * 70)
                            return

                        await log_line(
                            f"[TRY] Seite {page_num}, Fall {idx + 1}/{len(cards)} "
                            f"| Slot 1: {slot1_accepted}/{slot1_max} | Slot 2: {slot2_accepted}/{slot2_max}"
                        )

                        # ── Slot-Routing: prüfe Fall gegen Slot 1 und Slot 2 ─────
                        matched_slot = None
                        matched_filters = None
                        overlap_time = None

                        # Slot 1 prüfen (wenn noch nicht voll)
                        if not slot1_full:
                            try:
                                matches1, ot1 = await check_case_matches_filters(card, slot1_filters)
                                if matches1:
                                    matched_slot = 1
                                    matched_filters = slot1_filters
                                    overlap_time = ot1
                            except Exception as e:
                                await log_line(f"[WARN] Slot-1-Filter-Prüfung fehlgeschlagen: {e}")

                        # Slot 2 prüfen (nur wenn Slot 1 NICHT bereits zugewiesen wurde, aktiv und noch nicht voll)
                        # FIX: matched_slot == None verhindert, dass Slot 2 den bereits gesetzten Slot 1 überschreibt
                        if matched_slot is None and slot2_enabled and slot2_filters and not slot2_full:
                            try:
                                matches2, ot2 = await check_case_matches_filters(card, slot2_filters)
                                if matches2:
                                    matched_slot = 2
                                    matched_filters = slot2_filters
                                    overlap_time = ot2
                            except Exception as e:
                                await log_line(f"[WARN] Slot-2-Filter-Prüfung fehlgeschlagen: {e}")

                        # Wenn kein Slot passt, überspringen
                        if matched_slot is None:
                            await log_line(f"[SKIP] Fall {idx + 1} entspricht keinem Slot-Filter - übersprungen")
                            continue

                        # Button innerhalb der Karte robust ermitteln
                        btn = None
                        try:
                            containers = [card]
                            try:
                                parent = await card.evaluate_handle('el => el.parentElement')
                                containers.append(parent)
                                grand = await parent.evaluate_handle('el => el.parentElement')
                                containers.append(grand)
                            except Exception:
                                pass

                            for scope in containers:
                                candidate = await scope.query_selector("button[data-cy='submit']")
                                if candidate:
                                    btn = candidate
                                    break
                                try:
                                    loc = scope.get_by_role("button", name=_re.compile(r"Anfrage\s+(übernehmen|uebernehmen)", _re.I))
                                    if await loc.count() > 0:
                                        btn = loc.first
                                        break
                                except Exception:
                                    pass
                                candidate = await scope.query_selector("button:has-text('Übernehmen')")
                                if candidate:
                                    btn = candidate
                                    break
                        except Exception as e:
                            await log_line(f"[ERROR] Button-Suche fehlgeschlagen: {e}")
                            btn = None

                        if not btn:
                            await log_line(f"[SKIP] Fall {idx + 1} hat keinen erkennbaren 'Übernehmen'-Button (auch nicht im Parent)")
                            continue

                        # ── FIX: Karte und Button direkt vor Klick frisch aus DOM holen ──
                        # Zwischen Filter-Prüfung und Klick kann React die Seite neu gerendert haben
                        # → altes Element-Handle ist dann "not attached to the DOM".
                        # Lösung: Karte per Index nochmal frisch abfragen.
                        try:
                            fresh_cards = await page.query_selector_all("[data-testid='link-treatment-view']")
                            if idx < len(fresh_cards):
                                fresh_card = fresh_cards[idx]
                                # Button im frischen Element suchen
                                fresh_btn = None
                                fresh_containers = [fresh_card]
                                try:
                                    fp = await fresh_card.evaluate_handle('el => el.parentElement')
                                    fresh_containers.append(fp)
                                    fg = await fp.evaluate_handle('el => el.parentElement')
                                    fresh_containers.append(fg)
                                except Exception:
                                    pass
                                for scope in fresh_containers:
                                    c = await scope.query_selector("button[data-cy='submit']")
                                    if c:
                                        fresh_btn = c
                                        break
                                    c = await scope.query_selector("button:has-text('Übernehmen')")
                                    if c:
                                        fresh_btn = c
                                        break
                                if fresh_btn:
                                    btn = fresh_btn
                                    card = fresh_card
                                    await log_line(f"[INFO] Karte {idx + 1} frisch aus DOM geholt.")
                                else:
                                    await log_line(f"[SKIP] Karte {idx + 1}: kein Button im frischen DOM — übersprungen.")
                                    continue
                            else:
                                await log_line(f"[SKIP] Karte {idx + 1} nicht mehr im DOM (Seite hat sich verändert) — übersprungen.")
                                continue
                        except Exception as refresh_err:
                            await log_line(f"[WARN] DOM-Refresh fehlgeschlagen, nutze gecachtes Handle: {refresh_err}")

                        # Falls Filter übereinstimmen, versuche zu übernehmen (mit berechneter Zeit)
                        ok = await handle_case(page, btn, matched_filters, overlap_time, case_element=card)
                        if ok:
                            if matched_slot == 1:
                                slot1_accepted += 1
                            elif matched_slot == 2:
                                slot2_accepted += 1
                            await log_line(f"[DONE] ✅ Fall {idx + 1} erfolgreich übernommen! Slot {matched_slot}")
                            await asyncio.sleep(2)

                    # Weiter zur nächsten Seite — per URL (zuverlässiger als Button-Suche).
                    # Wenn die aktuelle Seite 0 Anfragen hatte, gibt es keine weiteren Seiten.
                    if len(cards) == 0 or page_num >= max_pages:
                        break

                # Prüfe nach jedem kompletten Scan, ob alle Slots voll
                slot1_full = slot1_accepted >= slot1_max
                slot2_full = (not slot2_enabled) or (slot2_accepted >= slot2_max)
                if slot1_full and slot2_full:
                    await log_line("=" * 70)
                    await log_line(f"[STOP] 🎯 Alle Slots voll: Slot 1 {slot1_accepted}/{slot1_max} | Slot 2 {slot2_accepted}/{slot2_max}")
                    await log_line("[STOP] Bot wird beendet. Alle gewünschten Patienten übernommen!")
                    await log_line("=" * 70)
                    return

                await log_line(
                    f"[LOOP] {total_found} Anfragen gefunden | "
                    f"Slot 1: {slot1_accepted}/{slot1_max} | Slot 2: {slot2_accepted}/{slot2_max}"
                )
                await log_line(f"[LOOP] Warte {scan_interval}s bis zum nächsten Scan...")
                await asyncio.sleep(scan_interval)

            except PlaywrightTimeoutError:
                await log_line("[WARN] Timeout beim Laden der Seite – Neustartversuch.")
                await asyncio.sleep(5)
            except Exception as e:
                await log_line(f"[ERROR] Unerwarteter Fehler im Loop: {e}")
                await asyncio.sleep(5)

def get_target_date(filters: dict) -> str:
    """Bestimmt das Zieldatum passend zum day_window-Filter."""
    day_window = normalize_text(filters.get("time_filter", {}).get("day_window", "heute"))
    now = datetime.now()
    if day_window == "morgen":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if day_window == "später":
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

async def main():
    """Hauptfunktion: lädt Filter und startet den Click-Loop."""
    global patients_accepted

    # Robuster Start: Kein Löschen der Log-Datei (vermeidet WinError 32 bei Datei-Lock).
    # Stattdessen schreiben wir einen Session-Header im Append-Modus.
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write("\n" + "=" * 70 + "\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Neue Bot-Session gestartet\n")
    except Exception as e:
        print(f"[WARN] Konnte Session-Header nicht in Log schreiben: {e}")

    filters = await load_filters()
    if not filters:
        await log_line("[FATAL] Filterdaten nicht verfügbar – Programmende.")
        return

    # RESET: Nur Zähler auf 0 — Slots und Patienten werden in click_loop()
    # nach Chrome-Start frisch aus Teleclinic importiert.
    patients_accepted = 0
    target_date = get_target_date(filters)
    await log_line(f"[RESET] Patient-Counter auf 0 zurückgesetzt für {target_date}")


    try:
        await click_loop(filters)
    except KeyboardInterrupt:
        await log_line("[EXIT] Manuell abgebrochen.")
    except Exception as e:
        await log_line(f"[FATAL] Unerwarteter Abbruch: {e}")
    finally:
        await log_line("[SHUTDOWN] TeleClinic Clicker beendet.")
        # Chrome-Prozess läuft weiter, da der Benutzer möglicherweise noch eingeloggt bleiben möchte


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        msg = f"[FATAL] Hauptfehler: {e}"
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
