#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_appointments_helper.py
-------------------------------
Wiederverwendbare Funktion zum Auslesen der Bestandstermine aus Teleclinic.
Wird von tc_main_gui.py beim GUI-Start aufgerufen (KEIN input(), kein interaktiver Block).
Die Funktion nutzt dieselbe Logik wie test_import_standalone.py, ist aber
vollständig nicht-interaktiv und GUI-kompatibel.

Aufruf:
    from import_appointments_helper import run_import_once
    result = await run_import_once(log_callback=self.log)
"""

import asyncio
import re
import socket
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Karten-Parse-JS (identisch mit test_import_standalone.py)
# ---------------------------------------------------------------------------
PARSE_CARDS_JS = """() => {
    const results = [];
    const bodyText = document.body.innerText || '';
    const dateMatch = bodyText.match(/(Heute|Morgen|Sp\\u00e4ter)[,\\s]+(\\d{1,2})\\.(\\s*\\w+)?(\\s*\\d{4})?/i);
    const pageDate = dateMatch ? dateMatch[0].trim() : '';

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
                cards.add(el); break;
            }
            el = el.parentElement;
        }
    }

    if (cards.size === 0) {
        const selectors = [
            '[data-testid*="appointment"]', '[data-testid*="treatment"]',
            '[class*="appointment"]', '[class*="treatment"]',
            '[class*="case"]', '[class*="card"]'
        ];
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) {
                const text = (el.innerText || '').trim();
                if (/\\d{1,2}:\\d{2}/.test(text) && text.length > 15) cards.add(el);
            }
            if (cards.size > 0) break;
        }
    }

    if (cards.size === 0) {
        for (const el of document.querySelectorAll('li, article')) {
            const text = (el.innerText || '').trim();
            if (/\\d{1,2}:\\d{2}/.test(text) && text.length > 15) cards.add(el);
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
        let diagnosis = '', wishes = '', gender = '', age = '', language = '';
        const skip = [
            /^\\d{1,2}:\\d{2}(\\s*Uhr)?$/,
            /^(video|gkv|pkv|privat|selbstzahler|termin stornieren|zum fall|mehr infos)$/i,
            /^\\d{1,2}\\.\\d{1,2}(\\.\\d{2,4})?$/,
            /^\\d+\\s*km$/i,
            /^(morgen|heute|sp\\u00e4ter)/i
        ];
        let diagFound = false;
        for (const line of lines) {
            if (skip.some(p => p.test(line.trim()))) continue;
            if (!language && /(English|Englisch|T\\u00fcrk\\u00e7e|T\\u00fcrkisch|\\u0420\\u0443\\u0441\\u0441\\u043a\\u0438\\u0439|Arabisch|Franz\\u00f6sisch)/i.test(line)) {
                language = line.trim(); continue;
            }
            const genderAgeCombo = line.match(/(m\\u00e4nnlich|weiblich|divers|male|female)[,\\s]+(\\d{1,3})\\s*(J\\.?|Jahre?)?/i);
            if (genderAgeCombo) {
                if (!gender) gender = genderAgeCombo[1].trim();
                if (!age) age = genderAgeCombo[2];
                continue;
            }
            if (!gender && /(m\\u00e4nnlich|weiblich|divers|male|female)/i.test(line) &&
                !/(\\d{1,3})\\s*(J\\.?|Jahre?)/i.test(line)) {
                gender = line.trim(); continue;
            }
            const m = line.match(/(\\d{1,3})\\s*(J\\.?|Jahre?)/i);
            if (!age && m) { age = m[1]; continue; }
            if (!age && /^\\d{1,3}$/.test(line.trim())) { age = line.trim(); continue; }
            if (!wishes && /(AU|Rezept|Beratung|Krankschreib|Attest|\\u00dcberweisung|Bescheinigung)/i.test(line)) {
                wishes = line.trim(); continue;
            }
            if (!diagFound && line.length >= 3 &&
                !/(m\\u00e4nnlich|weiblich|male|female|divers|English|Englisch|Jahre|\\d+\\s*J\\.?)/i.test(line)) {
                diagnosis = line.trim(); diagFound = true; continue;
            }
        }
        results.push({ time: time_str, diagnosis, wishes, gender, age, language,
                       pageDate, rawText: text.substring(0, 300) });
    }
    return results;
}"""


def is_chrome_debug_running() -> bool:
    """Prüft ob Chrome im Debug-Modus auf Port 9222 läuft."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('localhost', 9222))
        s.close()
        return result == 0
    except Exception:
        return False


async def _scan_tab(page, tab_nr: int, tab_name: str, log) -> list:
    """Liest Bestandstermine für einen Tab (0=Heute, 1=Morgen)."""
    all_found = []
    for page_num in range(1, 6):
        url = f"https://med.teleclinic.com/myappointments?tab={tab_nr}&page={page_num}"
        log(f"📥 [IMPORT] Lade {tab_name} Seite {page_num}...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_selector(
                    '[class*="appointment"], [class*="treatment"], [data-testid*="appointment"], li',
                    timeout=8000
                )
            except Exception:
                pass
            await asyncio.sleep(2)

            current_url = page.url or ""
            if "myappointments" not in current_url:
                log(f"⚠️ [IMPORT] Umgeleitet → nicht eingeloggt? URL: {current_url}")
                break

            page_text = await page.evaluate("() => document.body.innerText")
            time_matches = re.findall(r'\d{1,2}:\d{2}(?:\s*Uhr)?', page_text)
            if not time_matches:
                log(f"📥 [IMPORT] Keine Uhrzeiten auf {tab_name} Seite {page_num} → Ende")
                break

            parsed = await page.evaluate(PARSE_CARDS_JS)
            if parsed:
                for e in parsed:
                    all_found.append({**e, "day": tab_name})
                log(f"📥 [IMPORT] {tab_name} Seite {page_num}: {len(parsed)} Termine gefunden")
            else:
                log(f"📥 [IMPORT] {tab_name} Seite {page_num}: keine strukturierten Termine")
                break

            has_next = await page.evaluate("""() =>
                document.querySelectorAll(
                    'a[href*="page="],button[aria-label*="Next"],button[aria-label*="next"],button[aria-label*="N\\u00e4chste"]'
                ).length > 0
            """)
            if not has_next:
                break

        except Exception as exc:
            log(f"⚠️ [IMPORT] Fehler bei {tab_name} Seite {page_num}: {exc}")
            break

    return all_found


async def run_import_once(log_callback=None, timeout_seconds: int = 60) -> dict:
    """
    Liest Bestandstermine aus Teleclinic (Heute + Morgen) und schreibt sie in
    scheduled_slots.json (Scheduler) + scheduled_patients.json (GUI-Kalender).

    Voraussetzung: Chrome muss bereits geöffnet und der Nutzer eingeloggt sein.
    (Die GUI startet Chrome beim Starten des Bots — daher sollte Chrome beim
     zweiten Aufruf dieser Funktion schon laufen.)

    Gibt zurück:
        {"heute": int, "morgen": int, "gesamt": int, "fehler": str|None}
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    result: dict = {"heute": 0, "morgen": 0, "gesamt": 0, "fehler": None}

    # Warte kurz auf Chrome (max timeout_seconds)
    log("📥 [IMPORT] Warte auf Chrome-Verbindung...")
    waited = 0
    while not is_chrome_debug_running() and waited < timeout_seconds:
        await asyncio.sleep(2)
        waited += 2

    if not is_chrome_debug_running():
        result["fehler"] = "Chrome nicht erreichbar (Port 9222)"
        log(f"⚠️ [IMPORT] {result['fehler']} — Import übersprungen")
        return result

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            except Exception as e:
                result["fehler"] = f"Chrome-Verbindung fehlgeschlagen: {e}"
                log(f"⚠️ [IMPORT] {result['fehler']}")
                return result

            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            pages = list(context.pages)
            page = next(
                (pg for pg in pages if "med.teleclinic.com" in (pg.url or "")),
                pages[0] if pages else await context.new_page()
            )

            log(f"📥 [IMPORT] Verbunden. Aktuelle URL: {page.url}")

            heute_raw = await _scan_tab(page, 0, "Heute", log)
            morgen_raw = await _scan_tab(page, 1, "Morgen", log)

            # Duplikat-Bereinigung (Heute hat Vorrang)
            heute_keys = {(e.get("time", ""), e.get("diagnosis", "")) for e in heute_raw}
            morgen = [e for e in morgen_raw
                      if (e.get("time", ""), e.get("diagnosis", "")) not in heute_keys]
            heute = heute_raw
            alle = heute + morgen

            log(f"📥 [IMPORT] Zusammenfassung: {len(heute)} heute | {len(morgen)} morgen | {len(alle)} gesamt")

            if not alle:
                log("📥 [IMPORT] Keine Bestandstermine gefunden — Scheduler unverändert")
                return result

            # In Scheduler schreiben
            try:
                from core_scheduler import import_existing_appointments
                date_heute = datetime.now().strftime("%Y-%m-%d")
                date_morgen = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                scheduler_result = import_existing_appointments(alle, date_heute, date_morgen)
                log(f"📥 [IMPORT] Scheduler aktualisiert: "
                    f"Heute {scheduler_result['heute']} | Morgen {scheduler_result['morgen']} | "
                    f"Neu: {scheduler_result['neu_hinzugefuegt']}")
            except Exception as e:
                log(f"⚠️ [IMPORT] Scheduler-Fehler: {e}")

            # In GUI-Kalender schreiben
            try:
                from scheduled_patients import add_imported_appointment
                date_heute = datetime.now().strftime("%Y-%m-%d")
                date_morgen = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                gui_neu = 0
                for e in alle:
                    t = e.get("time", "")
                    if not t:
                        continue
                    day_label = e.get("day", "Heute")
                    date_key = date_morgen if day_label == "Morgen" else date_heute

                    # Sicherstellen: diagnosis = Krankheitsbild, wishes = Wunschleistung (AU, Rezept…)
                    diag_val  = (e.get("diagnosis") or "").strip() or "Extern terminiert"
                    wish_val  = (e.get("wishes")   or "").strip()
                    gend_val  = (e.get("gender")   or "").strip()
                    age_val   = (e.get("age")      or "").strip()

                    add_imported_appointment(
                        time=t,
                        date=date_key,
                        diagnosis=diag_val,
                        wishes=wish_val,
                        gender=gend_val,
                        age=age_val,
                    )
                    gui_neu += 1
                log(f"📥 [IMPORT] GUI-Kalender: {gui_neu} Termine eingetragen")
            except Exception as e:
                log(f"⚠️ [IMPORT] GUI-Kalender-Fehler: {e}")

            result["heute"] = len(heute)
            result["morgen"] = len(morgen)
            result["gesamt"] = len(alle)
            return result

    except Exception as e:
        result["fehler"] = str(e)
        log(f"❌ [IMPORT] Unerwarteter Fehler: {e}")
        return result
