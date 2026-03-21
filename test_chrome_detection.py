#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Chrome-Erkennung und Login-Wartezeit
"""

import socket
import time

def is_chrome_running():
    """Prüft ob Chrome auf Port 9222 läuft"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 9222))
        sock.close()
        return result == 0
    except Exception:
        return False

print("\n" + "="*80)
print("TEST: Intelligente Chrome-Erkennung und Login-Wartezeit")
print("="*80 + "\n")

# Test 1: Prüfe ob Chrome läuft
print("1️⃣  CHROME-STATUS-PRÜFUNG")
print("-" * 80)

if is_chrome_running():
    print("  ✅ Chrome läuft bereits im Debug-Modus (Port 9222)")
    print("  ✅ Login-Wartezeit wird ÜBERSPRUNGEN (sofortiger Start)")
    print("")
    print("  💡 Vorteil: Bot startet SOFORT, keine 90 Sekunden Wartezeit!")
else:
    print("  ℹ️  Chrome läuft NICHT im Debug-Modus")
    print("  ⏱️  Bei Bot-Start: 90 Sekunden Wartezeit für Login")
    print("")
    print("  💡 Tipp: Lassen Sie Chrome im Debug-Modus laufen für schnellere Starts!")

print("\n" + "="*80)
print("2️⃣  WIE ES FUNKTIONIERT")
print("="*80 + "\n")

print("""
SZENARIO 1: Chrome läuft NICHT (Erster Start des Tages)
  1. Bot startet Chrome im Debug-Modus
  2. Zeigt Login-Hinweis an
  3. Wartet 90 Sekunden (oder ENTER)
  4. Startet Scanning
  
  ⏱️  Zeit: ~90 Sekunden Wartezeit

SZENARIO 2: Chrome läuft BEREITS (Sie bleiben eingeloggt)
  1. Bot erkennt: Chrome läuft schon!
  2. Überspringt Chrome-Start
  3. Überspringt Login-Wartezeit
  4. Startet SOFORT mit Scanning
  
  ⚡ Zeit: 0 Sekunden Wartezeit (SOFORTIGER START!)

💡 EMPFEHLUNG:
  - Lassen Sie Chrome im Debug-Modus OFFEN nach dem ersten Login
  - Bei jedem weiteren Bot-Start: SOFORTIGER Start ohne Wartezeit!
  - Chrome schließt sich nicht automatisch - bleibt eingeloggt
""")

print("="*80)
print("3️⃣  TECHNISCHE DETAILS")
print("="*80 + "\n")

print("""
Die Erkennung funktioniert durch:
  ✅ Socket-Verbindung zu localhost:9222 (Chrome Debug Port)
  ✅ Timeout von 1 Sekunde (schnell und zuverlässig)
  ✅ Keine Abhängigkeit von Prozess-Namen oder PIDs
  
Vorteile:
  ✅ Funktioniert auch wenn Chrome von anderer Quelle gestartet wurde
  ✅ Plattformunabhängig (Windows, Mac, Linux)
  ✅ Kein Risiko von mehreren Chrome-Instanzen
  ✅ Respektiert bestehende Sessions (bleibt eingeloggt)
""")

print("="*80 + "\n")
