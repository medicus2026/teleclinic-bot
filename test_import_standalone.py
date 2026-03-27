#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_import_standalone.py
- Startet Chrome selbst (kein GUI nötig)
- Wartet auf Login per ENTER
- Liest Bestandstermine aus 'Meine offene Fälle' — HEUTE und MORGEN
- Zeigt alles im Terminal an (kein Klicken, kein Speichern)
"""

import asyncio
import json
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from core_scheduler import import_existing_appointments


def get_tab_from_filters() -> tuple:
    """Liest day_window aus filters.json → gibt (tab_nr, name) zurück."""
    try:
        data = json.loads((ROOT / "filters.json").read_text(encoding="utf-8"))
        day_window = data.get("time_filter", {}).get("day_window", "heute").strip().lower()
        if day_window == "morgen":
            return 1, "Morgen"
        elif day_window == "später":
            return 2, "Später"
        return 0, "Heute"
    except Exception as e:
        print(f"[WARN] filters.json nicht lesbar ({e}) → Tab=0 (Heute)")
        return 0, "Heute"


def is_chrome_running() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('localhost', 9222))
        s.close()
        return result == 0
    except Exception:
        return False


def start_chrome():
    """Startet Chrome im Debug-Modus falls noch nicht läuft."""
    if is_chrome_running():
        print("[OK] Chrome läuft bereits (Port 9222) — kein Neustart nötig")
        return None

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    chrome_exe = next((str(p) for p in chrome_paths if Path(p).exists()), None)

    if not chrome_exe:
        print("[FEHLER] Chrome nicht gefunden!")
        return None

    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + str(ROOT / "chrome_profile"),
        "--lang=de",
        "https://med.teleclinic.com/myappointments"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[OK] Chrome gestartet (PID: {proc.pid})")
    time.sleep(4)
    return proc


# ---------------------------------------------------------------------------
# Karten-Parse-JS (wird in scan_tab wiederverwendet)
# ---------------------------------------------------------------------------
PARSE_CARDS_JS = """() => {
    const results = [];

    // Datum aus Seitentext extrahieren (z.B. "Morgen, 27. März 2026" oder "Heute, 26. März 2026")
    const bodyText = document.body.innerText || '';
    const dateMatch = bodyText.match(/(Heute|Morgen|Später)[,\\s]+(\\d{1,2})\\.(\\s*\\w+)?(\\s*\\d{4})?/i);
    const pageDate = dateMatch ? dateMatch[0].trim() : '';

    // Strategie 1: Elemente die NUR eine Uhrzeit enthalten → Parent ist die Karte
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

    // Fallback: klassische Selektoren
    if (cards.size === 0) {
        const selectors = [
            '[data-testid*="appointment"]', '[data-testid*="treatment"]',
            '[class*="appointment"]', '[class*="treatment"]',
            '[class*="case"]', '[class*="card"]'
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

    // Fallback 2: li/article mit Uhrzeiten
    if (cards.size === 0) {
        for (const el of document.querySelectorAll('li, article')) {
            const text = (el.innerText || '').trim();
            if (/\\d{1,2}:\\d{2}/.test(text) && text.length > 15)
                cards.add(el);
        }
    }

    // Nur äußerste Elemente behalten
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
            /^(morgen|heute|später)/i
        ];
        let diagFound = false;
        for (const line of lines) {
            if (skip.some(p => p.test(line.trim()))) continue;
            if (!language && /(English|Englisch|Türkçe|Türkisch|Русский|Arabisch|Französisch)/i.test(line)) {
                language = line.trim(); continue;
            }
            if (!diagFound && line.length >= 3 &&
                !/(männlich|weiblich|male|female|divers|English|Englisch|Jahre|\\d+\\s*J\\.?)/i.test(line)) {
                diagnosis = line.trim(); diagFound = true; continue;
            }
            if (!wishes && /(AU|Rezept|Beratung|Krankschreib|Attest|Überweisung|Bescheinigung)/i.test(line)) {
                wishes = line.trim(); continue;
            }
            if (!gender && /(männlich|weiblich|divers|male|female)/i.test(line)) {
                gender = line.trim(); continue;
            }
            const m = line.match(/(\\d{1,3})\\s*(J\\.?|Jahre?)/i);
            if (!age && m) { age = m[1]; continue; }
            if (!age && /^\\d{1,3}$/.test(line.trim())) { age = line.trim(); }
        }
        results.push({ time: time_str, diagnosis, wishes, gender, age, language,
                       pageDate,
                       rawText: text.substring(0, 300) });
    }
    return results;
}"""


async def scan_tab(page, tab_nr: int, tab_name: str) -> list:
    """Liest alle Bestandstermine für einen Tab (0=Heute, 1=Morgen) aus."""
    all_found = []

    for page_num in range(1, 6):
        url = f"https://med.teleclinic.com/myappointments?tab={tab_nr}&page={page_num}"
        print(f"\n[SCAN {tab_name}] Lade: {url}")

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
                print(f"[WARN] Umgeleitet → {current_url} (nicht eingeloggt?)")
                break

            page_text = await page.evaluate("() => document.body.innerText")
            time_matches_raw = re.findall(r'\d{1,2}:\d{2}(?:\s*Uhr)?', page_text)
            print(f"[DEBUG] Zeitmuster auf Seite {page_num}: {time_matches_raw}")

            if not time_matches_raw:
                print(f"[INFO] Keine Uhrzeiten auf Seite {page_num} → Ende")
                break

            parsed = await page.evaluate(PARSE_CARDS_JS)

            if parsed:
                print(f"[ERGEBNIS] {len(parsed)} Termine auf Seite {page_num} ({tab_name}):")
                for e in parsed:
                    all_found.append({**e, "day": tab_name})
                    lang_info = f" | {e.get('language','')}" if e.get('language') else ""
                    print(f"  🕐 {e.get('time','?')} | {e.get('diagnosis','')} | "
                          f"{e.get('wishes','')} | {e.get('gender','')} | "
                          f"{e.get('age','')} J.{lang_info}")
                    print(f"     RAW: {repr(e.get('rawText','')[:140])}")
            else:
                print(f"[INFO] Keine strukturierten Termine auf Seite {page_num} ({tab_name})")
                print(f"[DEBUG] Seitentext: {repr(page_text[:400])}")
                break

            has_next = await page.evaluate("""() =>
                document.querySelectorAll(
                    'a[href*="page="],button[aria-label*="Next"],button[aria-label*="next"],button[aria-label*="Nächste"]'
                ).length > 0
            """)
            if not has_next:
                break

        except Exception as exc:
            import traceback
            print(f"[FEHLER] Seite {page_num} ({tab_name}): {exc}")
            traceback.print_exc()
            break

    return all_found


async def main():
    print("=" * 70)
    print("  TEST: Bestandstermine aus Teleclinic auslesen (HEUTE + MORGEN)")
    print("=" * 70)

    start_chrome()

    print("")
    print("  Bitte bei Teleclinic einloggen falls noch nicht geschehen.")
    print("  Drücke ENTER wenn du eingeloggt bist...")
    input()
    print("[OK] Starte Auslesen...")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("[OK] Mit Chrome verbunden")
        except Exception as e:
            print(f"[FEHLER] Verbindung zu Chrome fehlgeschlagen: {e}")
            return

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = list(context.pages)
        page = next((pg for pg in pages if "med.teleclinic.com" in (pg.url or "")), None)
        if not page:
            page = pages[0] if pages else await context.new_page()

        print(f"[INFO] Aktuelle URL: {page.url}")

        # BEIDE Tabs scannen — unabhängig von filters.json
        heute = await scan_tab(page, 0, "Heute")
        morgen = await scan_tab(page, 1, "Morgen")

        # Duplikat-Filter: Termine die bei Tab=0 UND Tab=1 auftauchen,
        # werden nur einmal gezählt (Tab=0 hat Vorrang → "Heute")
        morgen_dedupliziert = []
        heute_keys = {(e.get("time",""), e.get("diagnosis","")) for e in heute}
        for e in morgen:
            key = (e.get("time",""), e.get("diagnosis",""))
            if key not in heute_keys:
                morgen_dedupliziert.append(e)
            else:
                print(f"[DEDUP] Duplikat entfernt aus Morgen: {e.get('time','?')} | {e.get('diagnosis','')}")
        morgen = morgen_dedupliziert

        alle = heute + morgen

        print("\n" + "=" * 70)
        print(f"✅ ZUSAMMENFASSUNG: {len(heute)} heute | {len(morgen)} morgen | {len(alle)} gesamt")
        print("=" * 70)

        for label, gruppe in [("Heute", heute), ("Morgen", morgen)]:
            if gruppe:
                print(f"\n📅 {label} ({len(gruppe)} Termine):")
                print("-" * 60)
                for i, e in enumerate(gruppe, 1):
                    lang_info = f" | {e.get('language','')}" if e.get('language') else ""
                    print(f"  #{i:02d}  {e.get('time','?')} | {e.get('diagnosis','')} | "
                          f"{e.get('wishes','')} | {e.get('gender','')} | "
                          f"{e.get('age','')} J.{lang_info}")
            else:
                print(f"\n📅 {label}: keine Termine gefunden")

        # ── In Scheduler übertragen ──────────────────────────────────────────
        if alle:
            print("\n" + "=" * 70)
            print("  📥 Übertrage Bestandstermine in Scheduler (scheduled_slots.json)...")
            print("=" * 70)
            date_heute = datetime.now().strftime("%Y-%m-%d")
            date_morgen = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            ergebnis = import_existing_appointments(alle, date_heute, date_morgen)
            print(f"\n[OK] Scheduler aktualisiert:")
            print(f"     Heute  ({ergebnis['date_heute']}): {ergebnis['heute']}")
            print(f"     Morgen ({ergebnis['date_morgen']}): {ergebnis['morgen']}")
            print(f"     Neu hinzugefügt: {ergebnis['neu_hinzugefuegt']} Slots")
        else:
            print("\n[INFO] Keine Termine zum Importieren gefunden.")

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
