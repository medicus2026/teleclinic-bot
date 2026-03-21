# 🤖 TeleClinic Bot - Windows Installer Guide

## Installation auf Windows

### Schritt 1: Build vorbereiten (nur einmalig auf dem Entwicklungs-PC)

```bash
cd C:\teleclinic-bot
python build_exe.py
```

**Oder einfacher:** Doppelklick auf `BUILD_INSTALLER.bat`

Das Skript:
- ✅ Installiert PyInstaller
- ✅ Baut TeleClinic-Bot.exe
- ✅ Speichert in `dist/TeleClinic-Bot.exe`

### Schritt 2: Auf andere PCs kopieren

Nach dem Build:
1. Kopiere den Ordner `dist/` auf den anderen PC
2. Oder komprimiere ihn als `.zip` und schicke es per Mail/USB

**Struktur:**
```
TeleClinic-Bot/
├── TeleClinic-Bot.exe
├── filters.json  (wird automatisch erstellt)
└── [weitere Dateien]
```

### Schritt 3: Auf anderem PC starten

Doppelklick auf `TeleClinic-Bot.exe` → GUI öffnet sich automatisch

## Was die GUI kann

### Filter einstellen
- **Tag:** Heute / Morgen / Später
- **Zeit:** Von / Bis (HH:MM)
- **Alter:** Min / Max (leer = egal)
- **Sprache:** (leer = egal, z.B. "Englisch")
- **Diagnose:** (leer = egal, z.B. "Haut, Psychische Leiden")
- **Wünsche:** (leer = egal, z.B. "AU, Rezept")
- **Max Patienten:** 1-20

### Buttons
- **▶️ START** → Scanner & Clicker starten
  - Liest Filter
  - Verbindet mit Chrome (Debug-Modus)
  - Scannt & klickt automatisch
  - Live-Log anzeigen
  
- **⏹️ STOP** → Bot sofort stoppen

- **💾 Filter speichern** → Speichert Einstellungen in filters.json

- **❌ Programm beenden** → GUI schließen

### Automatisches Beenden
Der Bot beendet sich automatisch wenn:
- ✅ Max Patienten erreicht (z.B. 5)
- ✅ Sprechstundenende erreicht

## Voraussetzungen

### Auf jedem PC:
1. **Windows 7 oder neuer**
2. **Google Chrome** (bereits installiert)
   - Chrome wird im Debug-Modus gestartet
   - Du musst dich einmalig bei med.teleclinic.com einloggen
   
3. **Internetverbindung**

### Nicht nötig:
- ❌ Python (ist in .exe eingepackt)
- ❌ Playwright installieren (ist in .exe eingepackt)
- ❌ Dependencies installieren (alles fertig)

## Erste Verwendung

1. **Starte TeleClinic-Bot.exe**
2. **Stelle Filter ein** (Zeit, Alter, Sprache, etc.)
3. **Klick START**
4. Chrome öffnet sich im Debug-Modus
5. **Manuell einloggen** bei med.teleclinic.com (SMS-Code eingeben)
6. **ENTER drücken** oder nach 90s: Bot startet automatisch
7. Scanner & Clicker laufen → Live-Log zeigt Fortschritt
8. ✅ Patientenfälle werden automatisch geklickt

## Troubleshooting

### Problem: "Chrome nicht gefunden"
**Lösung:** Installiere Google Chrome von https://www.google.com/chrome/

### Problem: "Verbindung zu Chrome fehlgeschlagen"
**Lösung:** 
- Chrome hat sich geschlossen → TeleClinic-Bot.exe neu starten
- Debug-Port 9222 ist belegt → Neustart des PCs

### Problem: Bot klickt nicht
**Lösung:**
- Prüfe ob du bei med.teleclinic.com eingeloggt bist
- Prüfe die Filter (Zeit, Diagnose, Alter, etc.)
- Schau ins Live-Log für Error-Meldungen

## Logs & Debugging

**Log-Datei:** `tc_click_log.txt` (im gleichen Ordner wie .exe)

Zeigt:
- Scanner-Status
- Filter-Matches/Skips
- Fehler beim Klicken
- Automatisches Beenden

## Fragen?

Siehe: HYBRID_SYSTEM_INFO.md für technische Details

---

**Version:** 1.0 (2026-01-25)
**Entwickelt für:** Windows 10/11
