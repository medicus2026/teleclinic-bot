# teleclinic_click_from_list_v9d.py
# Vollständige, überarbeitete Version mit Scheduler-Integration
# Asynchrone Version (Playwright async_api)

import asyncio
import json
import subprocess
import time
import threading
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Scheduler-Modul
from core_scheduler import next_available_slot, validate_max_patients, reset_slots_for_date

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
    print(line)
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
    input()  # Blockiert bis ENTER gedrückt wird
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

        # ZEIT-FILTER: Prüfe Überschneidung mit Sprechstundenzeit
        overlap_start_time = None
        patient_start, patient_end = parse_time_range(case_text)
        # WICHTIG: Explizite None-Prüfung, nicht "if patient_start and patient_end"!
        # Grund: patient_end = 0 (Mitternacht) ist falsy, würde übersprungen
        if patient_start is not None and patient_end is not None:
            treatment_start_str = filters['time_filter']['treatment_start']
            treatment_end_str = filters['time_filter']['treatment_end']
            treatment_start = time_to_minutes(treatment_start_str)
            treatment_end = time_to_minutes(treatment_end_str)

            # Berechne Überschneidung
            overlap_start_time = calculate_overlap_start(patient_start, patient_end,
                                                         treatment_start, treatment_end)

            if not overlap_start_time:
                await log_line(f"[FILTER] ❌ Keine Zeitüberschneidung!")
                await log_line(f"         Patient: {patient_start//60:02d}:{patient_start%60:02d} - {patient_end//60:02d}:{patient_end%60:02d}")
                await log_line(f"         Sprechstunde: {treatment_start_str} - {treatment_end_str}")
                return (False, None)
            else:
                await log_line(f"[FILTER] ✅ Zeitüberschneidung vorhanden: Start bei {overlap_start_time}")

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
            # Für jeden Include-Filter: prüfe alle Synonyme
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
    Startet Google Chrome im Debug-Modus auf Port 9222.
    Sucht automatisch nach der Chrome-Installation.
    WICHTIG: Erzwingt deutsche Locale (de-DE) für 24h-Zeit-Format!

    Returns:
        subprocess.Popen: Chrome-Prozess (oder None bei vorhandenem Chrome)
    """
    import socket

    # Prüfe ob Chrome bereits läuft (Port 9222 erreichbar)
    def is_chrome_running():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 9222))
            sock.close()
            return result == 0
        except Exception:
            return False

    if is_chrome_running():
        print("[INFO] Chrome läuft bereits im Debug-Modus (Port 9222)")
        print("[INFO] Überspringe Chrome-Start und Login-Wartezeit...")
        return None  # Signalisiert: Chrome läuft schon

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"
    ]

    chrome_exe = None
    for path in chrome_paths:
        if Path(path).exists():
            chrome_exe = str(path)
            break

    if not chrome_exe:
        print("[ERROR] Google Chrome nicht gefunden. Bitte manuell installieren.")
        return None

    # Chrome im Debug-Modus starten mit DEUTSCHER LOCALE
    # Das erzwingt 24h-Zeit-Format auf der ganzen Seite!
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + str(ROOT / "chrome_profile"),
        "--lang=de",  # 🔧 DEUTSCH - erzwingt 24h-Format!
        "https://med.teleclinic.com/"
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[OK] Google Chrome gestartet im Debug-Modus (PID: {process.pid})")
        print("[INFO] Chrome wird geladen mit deutscher Locale (24h-Format)...")
        time.sleep(3)
        print("")
        print("=" * 80)
        print("  🔐 BITTE JETZT EINLOGGEN!")
        print("=" * 80)
        print("  1. Loggen Sie sich bei med.teleclinic.com ein")
        print("  2. Geben Sie den SMS-Sicherheitscode ein")
        print("  3. Warten Sie, bis Sie auf der Startseite 'Behandlungsanfragen' sind")
        print("")
        print("  ⏱️  Das Programm wartet automatisch 90 Sekunden.")
        print("  ⚡ Oder drücken Sie ENTER, sobald Sie eingeloggt sind (schnellerer Start)")
        print("=" * 80)
        print("")

        # Starte Thread für ENTER-Erkennung
        enter_thread = threading.Thread(target=wait_for_enter, daemon=True)
        enter_thread.start()

        # Countdown mit Abbruch bei ENTER
        for i in range(90, 0, -5):
            if manual_start:
                print("")
                print("[OK] Manueller Start erkannt!")
                break
            print(f"  ⏳ Automatischer Start in {i} Sekunden... (oder ENTER drücken)", end="\r")
            time.sleep(5)

        if not manual_start:
            print("")
            print("[OK] Login-Zeit abgelaufen. Starte automatisches Scannen...")
        else:
            print("[OK] Starte automatisches Scannen...")

        time.sleep(2)
        return process
    except Exception as e:
        print(f"[ERROR] Konnte Chrome nicht starten: {e}")
        return None


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
            await case_button.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        try:
            await case_button.click(timeout=5000)
        except Exception as e:
            await log_line(f"[ERROR] Klick auf Karten-Button fehlgeschlagen: {e}")
            return False

        # Warte auf Dialog statt nur auf das Zeitfeld
        try:
            dlg = page.get_by_role("dialog")
            await dlg.first.wait_for(state="visible", timeout=10000)
        except Exception:
            # Fallback: warte kurz und prüfe direkt auf Time-Input
            await page.wait_for_timeout(1000)
        await log_line("[POPUP] Dialog/Popup erkannt (oder Time-Input erscheint gleich).")

        # WICHTIG: Nutze IMMER den Scheduler für korrekte Intervalle!
        # overlap_time wird als min_start_time übergeben (frühester erlaubter Start)
        slot = next_available_slot(filters, min_start_time=overlap_time)

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

        # Zeit in Feld schreiben
        try:
            await time_input.click()
            await time_input.fill(slot)
            await log_line(f"[OK] Termin {slot} eingetragen.")
        except Exception as e:
            await log_line(f"[ERROR] Konnte Zeit nicht eintragen: {e}")
            return False

        # Warte kurz damit die Eingabe verarbeitet wird
        await asyncio.sleep(0.6)

        # Robuste Eingabe: per Tastatur setzen und verifizieren; falls UI rundet, nächsten Intervall probieren
        try:
            # Hole Intervall-Minuten aus Filters
            interval_min = filters.get("runtime", {}).get("interval_minutes", 5)
            try:
                interval_min = int(interval_min)
            except Exception:
                interval_min = 5

            # Hilfsfunktion: addiere Minuten zu HH:MM
            def add_minutes(hhmm: str, delta: int) -> str:
                h, m = map(int, hhmm.split(":"))
                total = h*60 + m + delta
                return f"{total//60:02d}:{total%60:02d}"

            attempts = 0
            max_attempts = 6
            current_try = slot

            # Fokussiere Zeitfeld
            await time_input.click()
            await asyncio.sleep(0.3)

            # WICHTIG: Setze die Zeit direkt via JavaScript-Wert, nicht per type()
            # Das umgeht die 12h/AM-PM-Konvertierung des Browsers
            await time_input.evaluate(f"el => el.value = '{current_try}'")
            await time_input.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
            await time_input.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
            await asyncio.sleep(0.5)

            # Verifiziere Wert
            accepted = False
            try:
                val = await time_input.input_value()
            except Exception:
                val = None

            if val and val[:5] == current_try:
                accepted = True
                await log_line(f"[TIME] ✅ Zeit angenommen (JS): {current_try}")
            else:
                await log_line(f"[TIME] UI hat Zeit '{val}' statt '{current_try}' übernommen – versuche nächsten Intervall")

            # Bei Abweichung: iterativ nächstes Intervall probieren
            while not accepted and attempts < max_attempts:
                attempts += 1
                current_try = add_minutes(current_try, interval_min)

                # Setze Zeit wieder via JavaScript
                await time_input.click()
                await asyncio.sleep(0.2)
                await time_input.evaluate(f"el => el.value = '{current_try}'")
                await time_input.evaluate("el => el.dispatchEvent(new Event('input', {bubbles: true}))")
                await time_input.evaluate("el => el.dispatchEvent(new Event('change', {bubbles: true}))")
                await asyncio.sleep(0.5)

                try:
                    val = await time_input.input_value()
                except Exception:
                    val = None

                if val and val[:5] == current_try:
                    accepted = True
                    await log_line(f"[TIME] ✅ Akzeptierte Zeit (JS): {current_try}")
                    break
                else:
                    await log_line(f"[TIME] ❌ Zeit '{current_try}' nicht akzeptiert (UI zeigte '{val}')")

            if not accepted:
                await log_line("[ERROR] Keine akzeptierte Terminzeit gefunden – überspringe Fall.")
                # Schließe Popup
                try:
                    close_btn = page.get_by_role("button", name="Abbrechen").first
                    if await close_btn.count():
                        await close_btn.click()
                except Exception:
                    pass
                return False
        except Exception as e:
            await log_line(f"[ERROR] Konnte Zeit nicht setzen: {e}")
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
            await pickup.click(timeout=5000)
        except Exception as e:
            await log_line(f"[ERROR] Klick auf 'Übernehmen' fehlgeschlagen: {e}")
            return False

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


async def check_and_update_day_window(filters, last_midnight_check=None):
    """
    Prüft ob Mitternacht überschritten wurde und aktualisiert day_window Filter.
    Returns: (updated_filters, last_midnight_check_time)
    """
    now = datetime.now()
    current_time = now.time()

    if last_midnight_check:
        time_since_check = (now - last_midnight_check).total_seconds()
        if time_since_check < 30:
            return (filters, last_midnight_check)

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


async def click_loop(filters):
    """Durchsuche regelmäßig die Seite nach übernehmbaren Fällen."""
    global patients_accepted
    # Reset am Start eines jeden Laufs
    patients_accepted = 0
    await log_line("[RESET] Patientenanzahl auf 0 zurückgesetzt.")

    scan_interval = int(filters.get("loop", {}).get("scan_interval_sec", 10))
    max_pages = int(filters.get("loop", {}).get("max_pages", 5))  # Maximal zu scannende Seiten

    # Validiere max_patients gegen verfügbare Slots
    max_patients_requested, max_patients_possible, is_valid = validate_max_patients(filters)

    # Wenn nicht erreichbar, nutze max mögliche Anzahl
    if not is_valid:
        max_patients = max_patients_possible
        await log_line(f"[WARN] ⚠️ Max-Patientenzahl angepasst: {max_patients_requested} → {max_patients} (erreichbar)")
    else:
        max_patients = max_patients_requested

    await log_line(f"[INFO] Maximale Patientenanzahl: {max_patients}")
    await log_line(f"[INFO] Scan-Intervall: {scan_interval} Sekunden")
    await log_line(f"[INFO] Max. Seiten pro Scan: {max_pages}")

    # Für Overnight-Scans: Merke uns die letzte Mitternacht-Prüfung
    last_midnight_check = None

    async with async_playwright() as p:
        try:
            # Verbinde mit dem bereits laufenden Chrome im Debug-Modus
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            await log_line("[START] Verbunden mit Google Chrome Debug-Session.")

            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()

            # Prüfe aktuelle URL
            current_url = page.url
            await log_line(f"[INFO] Aktuelle URL: {current_url}")

            # HYBRID-ANSATZ: URL-Navigation mit Validierung
            day_window = filters.get("time_filter", {}).get("day_window", "heute")
            tab_num = get_tab_number(day_window)
            day_name = "Heute" if tab_num == 0 else ("Morgen" if tab_num == 1 else "Später")

            await log_line(f"[INFO] 🗓️ Tag-Filter: {day_name} (Methode: URL tab={tab_num} + Validierung)")
            await log_line(f"[INFO] 🌙 Overnight-Scanning aktiviert: Bei Mitternacht wird Filter automatisch aktualisiert")


            # Wenn nicht auf der richtigen Seite ODER falscher Tab, navigiere dorthin
            # Prüfe ob aktueller Tab stimmt (wichtig für Morgen/Später!)
            needs_navigation = (
                "med.teleclinic.com/requests" not in current_url or
                f"tab={tab_num}" not in current_url
            )

            if needs_navigation:
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
            await log_line(f"[ERROR] Konnte nicht mit Chrome verbinden: {e}")
            await log_line("[INFO] Stelle sicher, dass Chrome im Debug-Modus läuft.")
            return

        while True:
            try:
                # 🌙 OVERNIGHT-FEATURE: Prüfe ob Mitternacht überschritten wurde
                filters, last_midnight_check = await check_and_update_day_window(filters, last_midnight_check)

                # HYBRID-ANSATZ: Bestimme Tab und navigiere
                day_window = filters.get("time_filter", {}).get("day_window", "heute")
                tab_num = get_tab_number(day_window)

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
                        # Prüfe ob maximale Patientenanzahl erreicht
                        if patients_accepted >= max_patients:
                            await log_line("=" * 70)
                            await log_line(f"[STOP] 🎯 Maximale Patientenanzahl erreicht: {patients_accepted}/{max_patients}")
                            await log_line("[STOP] Bot wird beendet. Ziel erreicht!")
                            await log_line("=" * 70)
                            return  # Beende die Funktion komplett

                        await log_line(f"[TRY] Seite {page_num}, Fall {idx + 1}/{len(cards)} wird geprüft... (Patienten: {patients_accepted}/{max_patients})")

                        # Prüfe Filter BEVOR wir klicken
                        try:
                            # Prüfe ob Fall den Filtern entspricht (gibt Tuple zurück: (matches, overlap_time))
                            matches, overlap_time = await check_case_matches_filters(card, filters)
                            if not matches:
                                await log_line(f"[SKIP] Fall {idx + 1} entspricht nicht den Filtern - übersprungen")
                                continue

                        except Exception as e:
                            await log_line(f"[WARN] Konnte Filter nicht prüfen: {e} - versuche trotzdem")
                            overlap_time = None  # Fallback

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

                            import re as _re
                            for scope in containers:
                                # 1) Stabiler data-cy Selector
                                candidate = await scope.query_selector("button[data-cy='submit']")
                                if candidate:
                                    btn = candidate
                                    break
                                # 2) Role + Regex mit Ü/ue Fallback
                                try:
                                    loc = scope.get_by_role("button", name=_re.compile(r"Anfrage\s+(übernehmen|uebernehmen)", _re.I))
                                    if await loc.count() > 0:
                                        btn = loc.first
                                        break
                                except Exception:
                                    pass
                                # 3) Fallback: beliebiger Button mit Teiltext 'Übernehmen' oder 'Anfrage'
                                candidate = await scope.query_selector("button:has-text('Übernehmen')")
                                if candidate:
                                    btn = candidate
                                    break
                                candidate = await scope.query_selector("button:has-text('Anfrage')")
                                if candidate:
                                    btn = candidate
                                    break
                        except Exception as e:
                            await log_line(f"[ERROR] Button-Suche fehlgeschlagen: {e}")
                            btn = None

                        if not btn:
                            await log_line(f"[SKIP] Fall {idx + 1} hat keinen erkennbaren 'Übernehmen'-Button (auch nicht im Parent)")
                            continue

                        # Falls Filter übereinstimmen, versuche zu übernehmen (mit berechneter Zeit)
                        ok = await handle_case(page, btn, filters, overlap_time, case_element=card)
                        if ok:
                            await log_line(f"[DONE] ✅ Fall {idx + 1} erfolgreich übernommen!")
                            await asyncio.sleep(2)

                    # Prüfe, ob nächste Seite existiert (z.B. durch Pagination-Button)
                    next_button = await page.query_selector('button[aria-label="Next page"], a[aria-label="Next"]')
                    if not next_button or page_num >= max_pages:
                        break

                # Prüfe nach jedem kompletten Scan, ob Limit erreicht
                if patients_accepted >= max_patients:
                    await log_line("=" * 70)
                    await log_line(f"[STOP] 🎯 Maximale Patientenanzahl erreicht: {patients_accepted}/{max_patients}")
                    await log_line("[STOP] Bot wird beendet. Alle gewünschten Patienten übernommen!")
                    await log_line("=" * 70)
                    return

                await log_line(f"[LOOP] Gesamt {total_found} Anfragen gefunden. Patienten übernommen: {patients_accepted}/{max_patients}")
                await log_line(f"[LOOP] Warte {scan_interval}s bis zum nächsten Scan...")
                await asyncio.sleep(scan_interval)

            except PlaywrightTimeoutError:
                await log_line("[WARN] Timeout beim Laden der Seite – Neustartversuch.")
                await asyncio.sleep(5)
            except Exception as e:
                await log_line(f"[ERROR] Unerwarteter Fehler im Loop: {e}")
                await asyncio.sleep(5)

async def main():
    """Hauptfunktion: lädt Filter und startet den Click-Loop."""
    global patients_accepted

    # RESET: Lösche alte Log-Datei (damit Monitoring nicht alte Einträge liest)
    if LOG_PATH.exists():
        LOG_PATH.unlink()
        print("[START] 🗑️  Alte Log-Datei gelöscht - neuer Durchlauf startet sauber!")

    # RESET: Setze Counter auf 0 und lösche alte Slots beim Bot-Start
    patients_accepted = 0
    reset_slots_for_date()
    await log_line("[SCHEDULER] 🔄 Alte Termine für heute zurückgesetzt - neue Session startet!")
    await log_line(f"[RESET] Patient-Counter auf 0 zurückgesetzt")

    filters = await load_filters()
    if not filters:
        await log_line("[FATAL] Filterdaten nicht verfügbar – Programmende.")
        return

    # Starte Chrome im Debug-Modus (falls noch nicht gestartet)
    await log_line("[INFO] Prüfe Chrome Debug-Modus...")
    chrome_process = start_chrome_debug_mode()

    # chrome_process = None bedeutet: Chrome läuft bereits (OK!)
    # Nur wenn start_chrome_debug_mode() FEHLGESCHLAGEN ist, würde es eine Exception werfen

    if chrome_process:
        await log_line(f"[INFO] Chrome gestartet mit PID {chrome_process.pid}")
    else:
        await log_line("[INFO] Chrome läuft bereits - überspringe Login-Wartezeit")

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
        print(f"[FATAL] Hauptfehler: {e}")
