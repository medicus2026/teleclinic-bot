"""
Schnelltest: Bestehende Termine aus 'Meine offene Fälle' importieren.
Voraussetzung: Chrome läuft im Debug-Modus auf Port 9222 und ist eingeloggt.
"""
import asyncio
import re
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent

async def test_import():
    # Lade Filter für day_window
    filters = json.loads((ROOT / "filters.json").read_text(encoding="utf-8"))
    day_window = filters.get("time_filter", {}).get("day_window", "heute")

    # Tab-Mapping: heute=0, morgen=1
    tab = 1 if day_window == "morgen" else 0

    print(f"Day-Window: {day_window} -> Tab: {tab}")
    print(f"Oeffne: https://med.teleclinic.com/myappointments?tab={tab}&page=1")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]

        alle_zeiten = set()

        # Prüfe beide Tabs: 0=heute, 1=morgen
        for check_tab in [0, 1]:
            tab_name = "Heute" if check_tab == 0 else "Morgen"
            url = f"https://med.teleclinic.com/myappointments?tab={check_tab}&page=1"
            print(f"--- {tab_name} (tab={check_tab}) ---")

            # Immer frisch die erste verfügbare Seite holen
            pages = context.pages
            if not pages:
                page = await context.new_page()
            else:
                page = pages[0]

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                await asyncio.sleep(2)

                page_text = await page.evaluate("document.body.innerText")

                # Finde alle "HH:MM Uhr" Muster
                time_matches = re.findall(r'(\d{2}:\d{2})\s*Uhr', page_text)

                if time_matches:
                    unique = sorted(set(time_matches))
                    print(f"  {len(unique)} Termine: {', '.join(unique)}")
                    alle_zeiten.update(unique)
                else:
                    kurz = ' | '.join(line for line in page_text.split('\n') if line.strip())[:300]
                    print(f"  Keine Termine. Seiteninhalt: {kurz}")

            except Exception as e:
                print(f"  Fehler bei Tab {check_tab}: {e}")
            print()

        if alle_zeiten:
            print(f"==> Gesamt {len(alle_zeiten)} unique Termine gefunden:")
            for t in sorted(alle_zeiten):
                print(f"    {t} Uhr")
            print()
            print("Diese Zeiten wuerden in scheduled_slots.json als belegt markiert.")
        else:
            print("==> Keine Termine auf beiden Tabs gefunden.")

if __name__ == "__main__":
    asyncio.run(test_import())
