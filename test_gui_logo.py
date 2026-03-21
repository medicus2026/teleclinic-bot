Überschr#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test der GUI mit Logo"""

import sys
from pathlib import Path

# Prüfe ob Logo existiert
logo_path = Path(__file__).parent / "Logo GIZ Praxis neu.png"
if logo_path.exists():
    print(f"✅ Logo gefunden: {logo_path}")
    print(f"   Größe: {logo_path.stat().st_size} bytes")
else:
    print(f"❌ Logo NICHT gefunden: {logo_path}")
    sys.exit(1)

# Prüfe ob alle erforderlichen Module vorhanden sind
try:
    import tkinter as tk
    print("✅ tkinter verfügbar")
except ImportError:
    print("❌ tkinter nicht verfügbar")
    sys.exit(1)

try:
    from PIL import Image, ImageTk
    print("✅ PIL/Pillow verfügbar")
except ImportError:
    print("❌ PIL/Pillow nicht verfügbar")
    sys.exit(1)

# Test: Lade und resize das Bild
try:
    img = Image.open(logo_path)
    print(f"✅ Logo geladen: {img.size}")
    img.thumbnail((150, 60), Image.Resampling.LANCZOS)
    print(f"✅ Logo resized zu: {img.size}")
except Exception as e:
    print(f"❌ Fehler beim Laden/Resizen: {e}")
    sys.exit(1)

print("\n🎉 ALLE TESTS BESTANDEN - GUI sollte funktionieren!")
