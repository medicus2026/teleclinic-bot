# 📦 TeleClinic Bot - Installations-Anleitung

## ✅ Installation auf einem neuen PC

### Schritt 1: Installer kopieren
1. Kopiere die Datei `TeleClinic-Bot-Installer.exe` aus dem Ordner:
   ```
   C:\teleclinic-bot\Output\TeleClinic-Bot-Installer.exe
   ```
2. Übertrage sie auf den neuen PC (z.B. per USB-Stick, Netzwerk oder E-Mail)

### Schritt 2: Installation durchführen
1. **Doppelklick** auf `TeleClinic-Bot-Installer.exe` auf dem neuen PC
2. Folge dem Installations-Assistenten:
   - Bestätige die Installation in `C:\teleclinic-bot`
   - Wähle "Desktop-Icon erstellen" an
   - Klicke auf "Installieren"

### Schritt 3: Programm starten
1. Nach der Installation erscheint ein **Desktop-Icon** mit dem TeleClinic-Logo
2. **Doppelklick** auf das Desktop-Icon
3. Beim **ersten Start**:
   - Lizenzcode eingeben: `Hanbo2001!`
   - Dieser wird gespeichert und muss nur einmal eingegeben werden
4. Die GUI startet automatisch

### Schritt 4: Chrome einrichten (einmalig auf jedem PC)
1. **Wichtig**: Chrome muss im Debug-Modus laufen
2. Erstelle eine Verknüpfung für Chrome mit Debug-Modus:
   - Rechtsklick auf Desktop → "Neu" → "Verknüpfung"
   - Ziel: 
     ```
     "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\teleclinic-bot\chrome_profile"
     ```
   - Name: "Chrome Debug TeleClinic"
3. **Immer** Chrome über diese Verknüpfung starten, bevor du den Bot benutzt
4. In Chrome bei `med.teleclinic.com` einloggen

---

## 🔧 Was wird installiert?

Der Installer kopiert automatisch:
- ✅ TeleClinic Bot GUI (tc_main_gui.py)
- ✅ Scanner & Clicker (teleclinic_click_from_list_v9d.py)
- ✅ Scheduler (core_scheduler.py)
- ✅ Filter-Konfiguration (filters.json)
- ✅ Lizenzsystem (license_system.py)
- ✅ Alle notwendigen Logos und Hilfsdateien

**Wichtig**: Python und alle Abhängigkeiten sind NICHT im Installer enthalten!

---

## ⚙️ Voraussetzungen auf dem Ziel-PC

Auf dem neuen PC müssen folgende Programme installiert sein:

### 1. Python 3.11+
- Download: https://www.python.org/downloads/
- Bei Installation: "Add Python to PATH" aktivieren!

### 2. Python-Abhängigkeiten installieren
Nach der Installation des Bots:
1. Öffne PowerShell oder CMD als Administrator
2. Wechsle ins Verzeichnis:
   ```
   cd C:\teleclinic-bot
   ```
3. Installiere die Abhängigkeiten:
   ```
   pip install -r requirements.txt
   ```
4. Installiere Playwright-Browser:
   ```
   playwright install chromium
   ```

### 3. Google Chrome
- Download: https://www.google.com/chrome/
- Nach Installation Chrome Debug-Verknüpfung erstellen (siehe oben)

---

## 🚀 Schnellstart-Checkliste für neuen PC

- [ ] TeleClinic-Bot-Installer.exe kopiert und installiert
- [ ] Python 3.11+ installiert
- [ ] `pip install -r requirements.txt` ausgeführt
- [ ] `playwright install chromium` ausgeführt
- [ ] Google Chrome installiert
- [ ] Chrome Debug-Verknüpfung erstellt
- [ ] Bei erstem Start Lizenzcode eingegeben
- [ ] Chrome im Debug-Modus gestartet und bei TeleClinic eingeloggt
- [ ] TeleClinic Bot GUI gestartet und Filter konfiguriert

---

## 🔒 Lizenzsystem

**Lizenzcode**: `Hanbo2001!`

- Wird beim ersten Start abgefragt
- Wird hardwaregebunden gespeichert in `license.key`
- Muss auf jedem neuen PC einmalig eingegeben werden
- Das Programm ist an die Hardware gebunden und kann nicht einfach weitergegeben werden

---

## ❓ Problembehebung

### Problem: "Python not found"
**Lösung**: Python installieren und zu PATH hinzufügen

### Problem: "playwright not found"
**Lösung**: `pip install playwright` und `playwright install chromium`

### Problem: "Chrome connection failed"
**Lösung**: 
1. Chrome über Debug-Verknüpfung starten
2. Bei TeleClinic einloggen
3. Bot neu starten

### Problem: Lizenzcode wird bei jedem Start verlangt
**Lösung**: 
- Prüfe ob `license.key` im Ordner existiert
- Starte das Programm als Administrator

### Problem: Scanner findet keine Patienten
**Lösung**:
1. Filter in GUI prüfen
2. Chrome Debug-Modus aktiv?
3. Bei TeleClinic eingeloggt?
4. Zeitfenster und Diagnosefilter korrekt?

---

## 📞 Support

Bei Problemen die folgenden Dateien prüfen:
- `tc_click_log.txt` - Klick- und Scan-Protokoll
- `filters.json` - Aktuelle Filter-Einstellungen
- `scheduled_slots.json` - Belegte Termine

---

**Version**: 2.0.0 Stable  
**Stand**: 2026-01-28  
**Entwickelt für**: GIZ Praxis
