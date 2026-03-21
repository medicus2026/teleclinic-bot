# 🚀 TeleClinic Bot - Quick Start Guide

## 📍 Wo liegt das Projekt?

### **Hauptordner:**
```
C:\teleclinic-bot\
```

---

## 🎯 Wie starte ich den Bot?

### **Option 1: Desktop-Shortcut (EINFACHSTE METHODE)** ⭐
1. **Doppelklick** auf Desktop-Icon: `TeleClinic Bot`
2. GUI öffnet sich automatisch
3. Filter einstellen → START klicken
4. Fertig!

### **Option 2: Direkt die .exe starten**
1. Windows Explorer öffnen
2. Navigiere zu: `C:\teleclinic-bot\dist\`
3. Doppelklick auf: `TeleClinic-Bot.exe`

### **Option 3: Von Entwicklungs-Code (Python)**
Wenn du Änderungen gemacht hast:
```powershell
cd C:\teleclinic-bot
.\.venv\Scripts\python tc_main_gui.py
```

---

## 📂 Wichtige Dateien & ihre Speicherorte

### **Produktive Anwendung:**
| Datei | Pfad | Was macht sie? |
|-------|------|----------------|
| **TeleClinic-Bot.exe** | `C:\teleclinic-bot\dist\TeleClinic-Bot.exe` | Fertige Anwendung - starten! |
| **Desktop-Shortcut** | `C:\Users\Thomas\Desktop\TeleClinic Bot.lnk` | Shortcut zur .exe |
| **Filter-Config** | `C:\teleclinic-bot\filters.json` | Deine Filter-Einstellungen |
| **Live-Log** | `C:\teleclinic-bot\tc_click_log.txt` | Was der Bot gerade macht |

### **Entwicklungs-Dateien:**
| Datei | Pfad | Wann bearbeiten? |
|-------|------|------------------|
| **Scanner & Clicker** | `C:\teleclinic-bot\teleclinic_click_from_list_v9d.py` | Synonyme/Filter-Logik ändern |
| **GUI** | `C:\teleclinic-bot\tc_main_gui.py` | GUI-Layout/Buttons ändern |
| **Scheduler** | `C:\teleclinic-bot\core_scheduler.py` | Terminplanung ändern |
| **Build-Script** | `C:\teleclinic-bot\build_exe.py` | Neue .exe bauen |

---

## 🔄 Typische Workflows

### **1. Einfach nur nutzen (keine Code-Änderungen)**
```
Desktop → Doppelklick "TeleClinic Bot"
→ Filter einstellen
→ START
→ Fertig!
```

### **2. Filter dauerhaft ändern**
```
Desktop → Doppelklick "TeleClinic Bot"
→ Filter anpassen (Zeit, Alter, Diagnose...)
→ "Filter speichern" klicken
→ Beim nächsten Start sind die Filter gespeichert
```

### **3. Code ändern & neu bauen**
```powershell
# 1. Code bearbeiten
notepad C:\teleclinic-bot\teleclinic_click_from_list_v9d.py

# 2. Neu bauen
cd C:\teleclinic-bot
python build_exe.py

# 3. Neue .exe nutzen
# → Automatisch in dist/ gespeichert
```

### **4. Auf anderen PC installieren**
```
1. Kopiere ganzen Ordner: C:\teleclinic-bot\dist\
2. Auf anderem PC: Doppelklick TeleClinic-Bot.exe
3. Desktop-Shortcut erstellen:
   → Rechtsklick auf .exe
   → "Verknüpfung erstellen"
   → Verknüpfung auf Desktop ziehen
```

---

## 🔖 Lesezeichen / Schnellzugriff

### **Windows Explorer:**
1. Öffne `C:\teleclinic-bot`
2. Rechtsklick auf Ordner-Icon in Adressleiste
3. "An Schnellzugriff anheften"
→ Jetzt immer links im Explorer sichtbar!

### **PowerShell Alias (optional):**
Füge zu deinem PowerShell-Profil hinzu:
```powershell
# PowerShell öffnen und eingeben:
notepad $PROFILE

# Am Ende einfügen:
function tc { cd C:\teleclinic-bot }
function tcstart { & "C:\teleclinic-bot\dist\TeleClinic-Bot.exe" }

# Speichern & PowerShell neu starten
# Dann kannst du eingeben:
# tc       → wechselt in Projektordner
# tcstart  → startet die GUI
```

---

## 📱 Schnellzugriff-Cheatsheet

| Aufgabe | Schnellster Weg |
|---------|-----------------|
| **Bot starten** | Desktop → "TeleClinic Bot" |
| **Log ansehen** | `C:\teleclinic-bot\tc_click_log.txt` |
| **Filter ändern** | In der GUI → "Filter speichern" |
| **Code bearbeiten** | `C:\teleclinic-bot\teleclinic_click_from_list_v9d.py` |
| **Neu bauen** | `cd C:\teleclinic-bot` → `python build_exe.py` |
| **Projekt öffnen** | Windows-Schnellzugriff → "teleclinic-bot" |

---

## 🆘 Notfall: Projekt verloren?

### **Suche nach der .exe:**
```powershell
# Windows-Suche (WIN + S):
TeleClinic-Bot.exe

# Oder PowerShell:
Get-ChildItem C:\ -Recurse -Filter "TeleClinic-Bot.exe" -ErrorAction SilentlyContinue
```

### **Backup erstellen (WICHTIG!):**
```powershell
# Sichere das Projekt:
Copy-Item -Path "C:\teleclinic-bot" -Destination "C:\teleclinic-bot-backup-$(Get-Date -Format 'yyyy-MM-dd')" -Recurse

# Oder als ZIP:
Compress-Archive -Path "C:\teleclinic-bot" -DestinationPath "C:\teleclinic-bot-backup-$(Get-Date -Format 'yyyy-MM-dd').zip"
```

### **Cloud-Backup (optional):**
- OneDrive: `C:\teleclinic-bot` → in OneDrive-Ordner kopieren
- USB-Stick: Ganzen Ordner auf USB kopieren
- Git: `git init` im Ordner → auf GitHub pushen

---

## 📞 Wichtige Pfade zum Merken

```
Hauptordner:   C:\teleclinic-bot\
Anwendung:     C:\teleclinic-bot\dist\TeleClinic-Bot.exe
Desktop:       C:\Users\Thomas\Desktop\TeleClinic Bot.lnk
Filter:        C:\teleclinic-bot\filters.json
Log:           C:\teleclinic-bot\tc_click_log.txt
```

---

## 💡 Pro-Tipp: Projekt-Shortcut im Startmenü

```powershell
# PowerShell als Admin:
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\TeleClinic Bot.lnk")
$Shortcut.TargetPath = "C:\teleclinic-bot\dist\TeleClinic-Bot.exe"
$Shortcut.WorkingDirectory = "C:\teleclinic-bot"
$Shortcut.Save()

# Danach: WIN-Taste → "TeleClinic" tippen → ENTER
```

---

**Stand:** 2026-01-25  
**Speicherort dieses Guides:** `C:\teleclinic-bot\QUICK_START_GUIDE.md`
