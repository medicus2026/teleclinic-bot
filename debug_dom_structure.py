"""
Debug-Skript: Zeigt die echte DOM-Struktur von myappointments.
Hilft, den Selector zu reparieren.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent

async def debug_dom():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            if not browser.contexts:
                print("❌ Keine Browser-Kontexte gefunden. Chrome im Debug-Modus?")
                return

            context = browser.contexts[0]
            pages = context.pages
            if not pages:
                page = await context.new_page()
            else:
                page = pages[0]

            # Navigiere zu myappointments heute
            url = "https://med.teleclinic.com/myappointments?tab=0&page=1"
            print(f"📍 Öffne: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            await page.wait_for_timeout(1500)

            print("\n" + "="*80)
            print("DOM-STRUKTUR DER SEITE (erste 100 Zeilen):")
            print("="*80 + "\n")

            # Hole den ganzen HTML-Body
            html = await page.content()
            lines = html.split('\n')

            # Zeige nur die wichtigen Teile (mit Terminen)
            for i, line in enumerate(lines):
                # Filtere nach Zeilen mit "Uhr" oder "appointment" oder "card"
                if any(keyword in line.lower() for keyword in ['uhr', 'appointment', 'card', 'treatment', 'zeit', '18:']):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    print(f"[Zeile {i}]")
                    for j in range(start, end):
                        prefix = ">>>" if j == i else "   "
                        print(f"{prefix} {lines[j][:120]}")
                    print()

            print("\n" + "="*80)
            print("ALTERNATIV: evaluate() Test")
            print("="*80 + "\n")

            # Versuche mit simplem Selector
            result = await page.evaluate("""() => {
                const body = document.body.innerText;
                const lines = body.split('\\n');
                const timeLines = lines.filter(l => /\\d{1,2}:\\d{2}\\s+(Uhr|UHR)/.test(l));
                return {
                    totalLines: lines.length,
                    foundTimeLines: timeLines,
                    sampleHtml: document.body.innerHTML.substring(0, 500)
                };
            }""")

            print(f"Total Zeilen im Body: {result['totalLines']}")
            print(f"Zeilen mit Uhrzeit gefunden: {len(result['foundTimeLines'])}")
            for line in result['foundTimeLines'][:10]:
                print(f"  - {line.strip()}")

        except Exception as e:
            print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    asyncio.run(debug_dom())
