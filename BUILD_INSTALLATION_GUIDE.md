# 🚀 TeleClinic AutoBot - Build & Installation

## 📋 Übersicht

Sie haben **3 Möglichkeiten** zur Installation auf anderen PCs:

| Option | Passwortschutz | Komplexität | Empfehlung |
|--------|---------------|-------------|------------|
| **1. Professioneller Installer** | ✅ Ja (Hanbo2001!) | Mittel | ⭐⭐⭐ EMPFOHLEN |
| **2. Portables Paket (ZIP)** | ❌ Nein | Einfach | ⭐⭐ Gut für Tests |
| **3. Nur .exe** | ❌ Nein | Sehr einfach | ⭐ Nur für Entwicklung |

---

## 🔐 Option 1: Professioneller Installer mit Passwortschutz (EMPFOHLEN)

### Vorteile:
✅ **Passwortschutz** - Nur autorisierte Personen können installieren  
✅ **Professionell** - Wie kommerzieller Software-Installer  
✅ **Desktop-Icon** - Automatisch erstellt  
✅ **Saubere Deinstallation** - Über Windows Systemsteuerung  
✅ **Alle Dateien** - Werden korrekt installiert  

### Voraussetzung:
Inno Setup muss installiert sein: https://jrsoftware.org/isdl.php

### Build-Prozess:

```bash
# Schritt 1: Terminal öffnen
cd C:\teleclinic-bot
.\.venv\Scripts\activate

# Schritt 2: Installer bauen
python build_installer_pro.py

# Schritt 3: Warten (~2-5 Minuten)
# ...

# Fertig! Installer ist hier:
# C:\teleclinic-bot\installer\TeleClinic-Bot-Setup-v2.0.0.exe
```

### Installation auf Ziel-PC:

1. **Installer kopieren**
   - Kopiere `TeleClinic-Bot-Setup-v2.0.0.exe` auf USB-Stick
   - Kopiere auf Ziel-PC (z.B. Desktop)

2. **Installer starten**
   - Doppelklick auf Setup.exe
   - **Passwort-Abfrage erscheint!**

3. **Passwort eingeben**
   - Gib ein: `Hanbo2001!`
   - Ohne korrektes Passwort → Installation nicht möglich

4. **Installation durchführen**
   - Folge den Schritten
   - Wähle Installations-Ordner (Standard: C:\Programme\TeleClinic-Bot)
   - Desktop-Icon erstellen? → Ja

5. **Fertig!**
   - Desktop-Icon wurde erstellt
   - Programm kann gestartet werden

---

## 📦 Option 2: Portables Paket (ZIP) - Ohne Passwort

### Vorteile:
✅ **Einfach** - Nur entpacken und starten  
✅ **Portable** - Funktioniert auch von USB-Stick  
✅ **Kein Admin** - Keine Admin-Rechte nötig  

### Nachteile:
❌ **Kein Passwortschutz** - Jeder kann es nutzen  
❌ **Manuell** - Desktop-Icon muss selbst erstellt werden  

### Build-Prozess:

```bash
# Schritt 1: Terminal öffnen
cd C:\teleclinic-bot
.\.venv\Scripts\activate

# Schritt 2: Portables Paket bauen
python build_portable.py

# Fertig! ZIP ist hier:
# C:\teleclinic-bot\TeleClinic-Bot-Portable-v2.0.0.zip
```

### Installation auf Ziel-PC:

1. **ZIP kopieren**
   - Kopiere `TeleClinic-Bot-Portable-v2.0.0.zip` auf Ziel-PC

2. **Entpacken**
   - Rechtsklick → "Alle extrahieren..."
   - Z.B. nach `C:\Programme\TeleClinic-Bot\`

3. **Programm starten**
   - Doppelklick auf `TeleClinic-Bot.exe`

4. **Optional: Desktop-Icon erstellen**
   - Rechtsklick auf TeleClinic-Bot.exe
   - "Senden an" → "Desktop (Verknüpfung erstellen)"

---

## 💻 Option 3: Nur .exe (Einfachste Variante)

### Vorteile:
✅ **Sehr einfach** - Nur eine Datei  

### Nachteile:
❌ **Unvollständig** - Zusätzliche Dateien fehlen (filters.json, Logo)  
❌ **Kein Passwortschutz**  
❌ **Nicht empfohlen für Produktion**  

### Build-Prozess:

```bash
cd C:\teleclinic-bot
.\.venv\Scripts\activate
python build_portable.py

# .exe ist hier:
# C:\teleclinic-bot\dist\TeleClinic-Bot.exe
```

---

## 🔧 Passwort ändern

Falls Sie das Installations-Passwort ändern möchten:

### Methode 1: In build_installer_pro.py
```python
# Öffne: C:\teleclinic-bot\build_installer_pro.py
# Ändere Zeile 18:

VERSION = "2.0.0"
INSTALL_PASSWORD = "NeuesPasswort123!"  # HIER ÄNDERN
```

### Methode 2: Im Inno Setup Script
```iss
# Nach dem Build öffne:
# C:\teleclinic-bot\installer\TeleClinic-Bot-Setup.iss

# Ändere Zeile:
#define InstallPassword "NeuesPasswort123!"
```

Dann erneut `python build_installer_pro.py` ausführen.

---

## 📊 Größen-Vergleich

| Datei | Größe | Was ist drin? |
|-------|-------|---------------|
| TeleClinic-Bot.exe | ~50-80 MB | Nur Programm + Python Runtime |
| Portable-ZIP | ~60-90 MB | Programm + alle Dateien |
| Setup.exe | ~60-90 MB | Installer + Programm + Dateien |

---

## ⚙️ Systemvoraussetzungen (Ziel-PC)

### Minimum:
- **OS:** Windows 10/11 (64-bit)
- **RAM:** 4 GB
- **Disk:** 500 MB frei
- **Browser:** Google Chrome (wird bei Bedarf installiert)

### Empfohlen:
- **OS:** Windows 11
- **RAM:** 8 GB
- **Disk:** 1 GB frei
- **Internet:** Stabile Verbindung

---

## 🛠️ Troubleshooting

### Problem: "PyInstaller nicht gefunden"
```bash
.\.venv\Scripts\python -m pip install -U pyinstaller Pillow
```

### Problem: "Inno Setup nicht gefunden"
- **Lösung 1:** Installiere Inno Setup: https://jrsoftware.org/isdl.php
- **Lösung 2:** Nutze `build_portable.py` (ohne Inno Setup)

### Problem: ".exe startet nicht auf Ziel-PC"
- Prüfe ob Windows Defender die .exe blockiert
- Evtl. Windows Defender ausschalten für den Ordner
- Oder: Digitale Signatur hinzufügen (kostenpflichtig)

### Problem: "Passwort funktioniert nicht"
- Prüfe Groß-/Kleinschreibung: `Hanbo2001!` (H groß!)
- Prüfe ob Passwort beim Build korrekt gesetzt wurde

---

## 📞 Support & Hilfe

### Bei Build-Problemen:
1. Prüfe ob .venv aktiviert ist
2. Prüfe ob alle Dateien vorhanden sind
3. Schaue in die Build-Log-Ausgabe

### Bei Installations-Problemen:
1. Prüfe Windows Defender
2. Prüfe Admin-Rechte
3. Schaue in Windows Event Viewer

---

## 🎯 Empfohlener Workflow

### Für Produktiv-Einsatz:
```bash
# 1. Inno Setup installieren (einmalig)
# Download: https://jrsoftware.org/isdl.php

# 2. Professionellen Installer bauen
cd C:\teleclinic-bot
.\.venv\Scripts\activate
python build_installer_pro.py

# 3. Installer verteilen
# Datei: installer\TeleClinic-Bot-Setup-v2.0.0.exe
# Passwort: Hanbo2001!
```

### Für Tests / Quick-Deploy:
```bash
# Portables Paket bauen
python build_portable.py

# ZIP verteilen
# Datei: TeleClinic-Bot-Portable-v2.0.0.zip
```

---

## ✅ Checkliste vor Verteilung

- [ ] Programm getestet (Scanner, Klicker, GUI)
- [ ] Terminkalender funktioniert
- [ ] Logo wird angezeigt
- [ ] Filter können gespeichert werden
- [ ] Passwort notiert
- [ ] README/Anleitung beigelegt
- [ ] Support-Kontakt angegeben

---

## 🔐 Sicherheitshinweise

1. **Passwort sicher aufbewahren**
   - Nicht in E-Mails verschicken
   - Nur persönlich weitergeben
   - Bei Bedarf ändern

2. **Installer-Datei schützen**
   - Nicht auf öffentlichen Servern ablegen
   - Nur auf verschlüsselten USB-Sticks transportieren

3. **Zugriff kontrollieren**
   - Nur autorisierte Personen erhalten Installer + Passwort
   - Log führen wer Installation erhalten hat

---

## 📝 Version History

### v2.0.0 (04.02.2026)
- ✅ GUI-Terminkalender vollständig funktionsfähig
- ✅ Scheduler stabil (5-Minuten-Intervalle)
- ✅ Overnight-Scanning implementiert
- ✅ Passwortgeschützter Installer
- ✅ Portable Version verfügbar

---

**Viel Erfolg bei der Installation! 🚀**
