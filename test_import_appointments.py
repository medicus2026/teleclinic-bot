"""
Schnelltest: Bestehende Termine aus 'Meine offene Fälle' importieren.
Voraussetzung: Chrome läuft im Debug-Modus auf Port 9222 und ist eingeloggt.
"""
import asyncio
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
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            if not browser.contexts:
                raise RuntimeError("Keine Browser-Kontexte gefunden. Bitte sicherstellen, dass Chrome im Debug-Modus läuft.")
            context = browser.contexts[0]
        except Exception as e:
            print(f"Fehler beim Verbinden mit dem Browser: {e}")
            return

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
                # Kurze Extra-Wartezeit fuer dynamisch nachgeladene Inhalte
                await page.wait_for_timeout(1500)

                # Gezielter DOM-Ansatz: NUR echte Termin-Zeitangaben lesen
                # Nur Elemente mit exakt "HH:MM Uhr" - keine Tooltips, keine Anfahrtszeiten
                try:
                    time_matches_raw = await page.evaluate("""() => {
                        const results = [];
                        // Strategie 1: h3/h2 und Zeitcontainer
                        const allEls = document.querySelectorAll(
                            'h3, h2, [class*="time"], [class*="hour"], [class*="slot"], [class*="appointment"]'
                        );
                        allEls.forEach(el => {
                            const text = (el.innerText || el.textContent || '').trim();
                            const m = text.match(/^(\\d{1,2}):(\\d{2})\\s+Uhr$/);
                            if (m) results.push(m[1].padStart(2,'0') + ':' + m[2]);
                        });
                        // Strategie 2: Fallback Textnodes
                        if (results.length === 0) {
                            const walker = document.createTreeWalker(
                                document.body, NodeFilter.SHOW_TEXT, null, false
                            );
                            let node;
                            while ((node = walker.nextNode())) {
                                const text = node.textContent.trim();
                                const m = text.match(/^(\\d{1,2}):(\\d{2})\\s+Uhr$/);
                                if (m) results.push(m[1].padStart(2,'0') + ':' + m[2]);
                            }
                        }
                        return results;
                    }""")
                except Exception as eval_err:
                    print(f"  DOM-Auswertung fehlgeschlagen: {eval_err}")
                    time_matches_raw = []

                normalized_times = set(dict.fromkeys(time_matches_raw))

                if normalized_times:
                    unique = sorted(normalized_times)
                    print(f"  {len(unique)} Termine: {', '.join(unique)}")
                    alle_zeiten.update(unique)
                else:
                    print(f"  Keine Termine auf dieser Seite gefunden.")

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
