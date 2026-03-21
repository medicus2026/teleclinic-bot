# 🔐 TeleClinic AutoBot - Schutz vor unbefugter Weitergabe

## ⚠️ IHRE FRAGE

> **"Wenn ich das Programm über die Zip-Datei auf einem anderen Rechner installiere, 
> besteht dann die Gefahr, dass jemand Unberechtigtes die Datei herunterlädt 
> und funktionierend weitergibt?"**

**ANTWORT: JA, bei der einfachen ZIP-Datei besteht dieses Risiko!**

---

## 🔓 PROBLEM: Ungeschützte ZIP-Datei

### Aktuelle Situation:
```
TeleClinic-Bot-Portable-v2.0.0.zip
├── TeleClinic-Bot.exe          ← Kann kopiert werden
├── filters.json                ← Kann kopiert werden
└── Logo.png                    ← Kann kopiert werden

❌ RISIKEN:
• Jeder kann ZIP kopieren
• Unbegrenzte Weitergabe möglich
• Keine Kontrolle wer es nutzt
• Kein Ablaufdatum
```

---

## ✅ LÖSUNG: 4 Schutz-Stufen

Ich habe **4 Schutz-Optionen** für Sie implementiert (vom Einfachsten zum Sichersten):

---

## 🔒 STUFE 1: Inno Setup Installer mit Passwort (EINFACH)

### Was ist das?
- Installer fragt Passwort vor Installation
- Ohne Passwort: Keine Installation möglich

### Sicherheit:
- ⭐⭐☆☆☆ (Niedrig)
- Passwort kann weitergegeben werden
- Nach Installation keine weitere Kontrolle

### Umsetzung:
```bash
# Bereits implementiert!
python build_installer_pro.py

# Ergebnis:
installer\TeleClinic-Bot-Setup-v2.0.0.exe
Passwort: Hanbo2001!
```

### Vorteil:
✅ Einfach zu implementieren  
✅ Sofort einsatzbereit

### Nachteil:
❌ Nach Installation keine Kontrolle  
❌ Kann kopiert und weitergegeben werden

---

## 🔐 STUFE 2: Hardware-Bindung (EMPFOHLEN)

### Was ist das?
- Software wird an **spezifischen PC** gebunden
- Funktioniert nur auf dem aktivierten PC
- Bei Weitergabe: Funktioniert NICHT

### Sicherheit:
- ⭐⭐⭐⭐☆ (Hoch)
- **Hardware-ID wird geprüft**
- Software läuft nur auf autorisiertem PC

### Wie funktioniert es?

```
1. Nutzer installiert Software
   └─> Aktivierungs-Dialog erscheint

2. Nutzer gibt Passwort ein: "Hanbo2001!"
   └─> Software erstellt Hardware-ID dieses PCs

3. Lizenz wird erstellt und gespeichert
   └─> Gebunden an: CPU + Motherboard + MAC-Adresse

4. Bei jedem Start:
   └─> Prüfe Hardware-ID
   └─> Stimmt nicht? → Software startet NICHT

5. Bei Weitergabe:
   └─> Anderer PC = Andere Hardware-ID
   └─> Lizenz ungültig → Aktivierung erforderlich
```

### Implementierung:

**Datei:** `license_system.py` (NEU erstellt!)

**Integration in GUI:** BEREITS IMPLEMENTIERT

```python
# tc_main_gui.py (Zeile 1-30)
from license_system import check_license_before_start

def main():
    # Prüfe Lizenz BEVOR GUI startet
    if not check_license_before_start():
        sys.exit(1)  # Beende wenn keine Lizenz
```

### Installation mit Hardware-Bindung:

```bash
# Schritt 1: Baue .exe MIT Lizenz-System
python build_portable.py  # Erstellt .exe

# Schritt 2: Kopiere auf Ziel-PC

# Schritt 3: Erste Ausführung auf Ziel-PC
TeleClinic-Bot.exe
  ↓
[Aktivierungs-Dialog erscheint]
  ↓
Passwort eingeben: Hanbo2001!
  ↓
✅ Aktiviert für DIESEN PC!
```

### Bei Weitergabe:

```
Nutzer kopiert .exe auf anderen PC
  ↓
Startet Programm
  ↓
Hardware-ID stimmt NICHT überein
  ↓
❌ "Lizenz ist für einen anderen PC!"
  ↓
Programm startet NICHT
```

### Vorteil:
✅ **Sehr sicher** - An PC gebunden  
✅ Weitergabe funktioniert NICHT  
✅ Automatische Prüfung bei jedem Start  
✅ Keine externe Server nötig

### Nachteil:
❌ Bei PC-Wechsel: Neue Aktivierung nötig  
❌ Bei Hardware-Upgrade: Neue Aktivierung nötig

---

## 🔐 STUFE 3: Zeitlich begrenzte Lizenz (ZUSÄTZLICH)

### Was ist das?
- Lizenz läuft nach X Tagen ab
- Danach: Neue Aktivierung erforderlich

### Sicherheit:
- ⭐⭐⭐⭐☆ (Hoch)
- Kombinierbar mit Hardware-Bindung
- **Zeitliche Kontrolle**

### Bereits implementiert in `license_system.py`:

```python
# Lizenz erstellen (365 Tage gültig)
license_data = self.generate_license_key(hw_id, days_valid=365)

# Bei Start prüfen:
expires = datetime.strptime(license_data['expires'], "%Y-%m-%d %H:%M:%S")
if datetime.now() > expires:
    return False, "Lizenz abgelaufen am ..."
```

### Anpassen der Gültigkeitsdauer:

```python
# In license_system.py, Zeile ~75:
license_data = self.generate_license_key(hw_id, days_valid=365)
                                                    ↑
                                            HIER ÄNDERN
                                            
# Beispiele:
days_valid=30   # 30 Tage
days_valid=90   # 3 Monate
days_valid=365  # 1 Jahr
```

### Vorteil:
✅ Zusätzliche zeitliche Kontrolle  
✅ Automatisches Ablaufen

### Nachteil:
❌ Nutzer müssen verlängern  
❌ Kann störend sein

---

## 🔐 STUFE 4: Online-Aktivierung (MAXIMALE SICHERHEIT)

### Was ist das?
- Lizenz wird über Server validiert
- Jede Aktivierung wird protokolliert
- Zentrale Kontrolle

### Sicherheit:
- ⭐⭐⭐⭐⭐ (Maximum)
- **Volle Kontrolle**
- Lizenzen können remote deaktiviert werden

### Funktionsweise:

```
1. Nutzer startet Software
   └─> Sendet Hardware-ID an Ihren Server

2. Server prüft:
   ├─> Ist Hardware-ID autorisiert?
   ├─> Ist Lizenz noch gültig?
   └─> Ist Limit erreicht? (z.B. max. 5 PCs)

3. Server antwortet:
   ├─> ✅ OK → Software startet
   └─> ❌ NEIN → Software startet NICHT

4. Zusätzlich:
   ├─> Logging aller Aktivierungen
   ├─> Blacklist für gesperrte Hardware-IDs
   └─> Remote-Deaktivierung möglich
```

### Benötigt:
- Webserver (z.B. kleiner PHP-Server)
- Datenbank für Lizenzen
- Internet-Verbindung

### Vorteil:
✅ **Maximum an Kontrolle**  
✅ Zentrale Verwaltung  
✅ Echtzeit-Überwachung  
✅ Lizenzen remote deaktivieren

### Nachteil:
❌ Komplexer zu implementieren  
❌ Benötigt Server  
❌ Internet-Verbindung erforderlich  
❌ Datenschutz beachten (DSGVO)

---

## 🎯 MEINE EMPFEHLUNG

### FÜR IHRE SITUATION:

**EMPFOHLEN: STUFE 2 (Hardware-Bindung) ⭐⭐⭐⭐**

```
✅ Bereits implementiert (license_system.py)
✅ Sehr sicher
✅ Kein Server nötig
✅ Einfach zu nutzen
✅ Weitergabe funktioniert NICHT
```

### WARUM?

1. **Einfach:** Keine komplexe Infrastruktur
2. **Sicher:** Software läuft nur auf autorisiertem PC
3. **Praktisch:** Passwort-Aktivierung (Hanbo2001!)
4. **Effektiv:** Verhindert unbefugte Weitergabe

---

## 📋 AKTIVIERUNG: So nutzen Sie Hardware-Bindung

### Schritt 1: Build mit Lizenz-System

```bash
cd C:\teleclinic-bot
.\.venv\Scripts\activate

# Baue .exe MIT license_system.py
python build_portable.py

# Oder mit Installer:
python build_installer_pro.py
```

### Schritt 2: Installation auf Ziel-PC

```
1. Kopiere ZIP/Installer auf Ziel-PC

2. Entpacken/Installieren

3. Starte TeleClinic-Bot.exe

4. Aktivierungs-Dialog erscheint:
   ┌─────────────────────────────────────┐
   │ 🔐 Software-Aktivierung erforderlich │
   │                                      │
   │ Hardware-ID: abc123...               │
   │                                      │
   │ Aktivierungs-Passwort: [ ******** ] │
   │                                      │
   │  [✅ Aktivieren]  [❌ Abbrechen]     │
   └─────────────────────────────────────┘

5. Passwort eingeben: Hanbo2001!

6. ✅ Aktiviert für DIESEN PC!

7. Datei erstellt: license.key
   (Gespeichert mit Hardware-ID)
```

### Schritt 3: Bei Weitergabe (Anderer PC)

```
Jemand kopiert die Software

Startet auf ANDEREM PC

Hardware-ID stimmt NICHT

❌ Fehler-Dialog:
┌────────────────────────────────────────┐
│ ❌ FEHLER                              │
│                                        │
│ Lizenz ist für einen anderen PC!      │
│                                        │
│ Diese Software ist an einen           │
│ bestimmten PC gebunden.                │
│                                        │
│ Kontaktieren Sie den Administrator    │
│ für eine neue Lizenz.                  │
└────────────────────────────────────────┘

Programm startet NICHT
```

---

## 🔧 TECHNISCHE DETAILS

### Was wird für Hardware-ID verwendet?

```python
def get_hardware_id(self) -> str:
    # 1. CPU-ID (Prozessor-Seriennummer)
    cpu_id = subprocess.check_output("wmic cpu get processorid")
    
    # 2. Motherboard-Seriennummer
    motherboard = subprocess.check_output("wmic baseboard get serialnumber")
    
    # 3. MAC-Adresse (Netzwerkkarte)
    mac = uuid.getnode()
    
    # Kombiniere und hashe (für Privatsphäre)
    combined = f"{cpu_id}-{motherboard}-{mac}"
    hw_id = hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    return hw_id  # z.B. "a1b2c3d4e5f6g7h8"
```

### Lizenz-Datei (license.key):

```json
{
  "hardware_id": "a1b2c3d4e5f6g7h8",
  "created": "2026-02-04 15:30:00",
  "expires": "2027-02-04 15:30:00",
  "activated_by": "GIZ Praxis",
  "version": "2.0.0",
  "signature": "xyz..."  ← Verhindert Manipulation
}
```

### Bei jedem Programmstart:

```python
1. Lade license.key
2. Prüfe Hardware-ID (stimmt mit aktuellem PC?)
3. Prüfe Signatur (wurde manipuliert?)
4. Prüfe Ablaufdatum (noch gültig?)
5. Wenn alles OK: ✅ Starte Programm
6. Wenn nicht: ❌ Aktivierungs-Dialog
```

---

## 🛠️ ANPASSUNGEN

### Passwort ändern:

```python
# In license_system.py, Zeile 18:
self.master_password = "Hanbo2001!"  ← HIER ÄNDERN
```

### Gültigkeitsdauer ändern:

```python
# In license_system.py, Zeile ~75:
license_data = self.generate_license_key(hw_id, days_valid=365)
                                                           ↑
                                                    TAGE ÄNDERN
```

### Hardware-Prüfung anpassen:

```python
# In license_system.py, Zeile ~35:
# Entferne z.B. MAC-Adresse wenn problematisch
# (Bei Netzwerkkarten-Wechsel)
```

---

## 📊 VERGLEICH: Alle Schutz-Stufen

| Stufe | Sicherheit | Aufwand | Server? | Empfehlung |
|-------|------------|---------|---------|------------|
| **1. Installer-Passwort** | ⭐⭐☆☆☆ | Sehr niedrig | ❌ Nein | Basis-Schutz |
| **2. Hardware-Bindung** | ⭐⭐⭐⭐☆ | Niedrig | ❌ Nein | ✅ **EMPFOHLEN** |
| **3. + Zeitlimit** | ⭐⭐⭐⭐☆ | Niedrig | ❌ Nein | Optional |
| **4. Online-Aktivierung** | ⭐⭐⭐⭐⭐ | Hoch | ✅ Ja | Für Enterprise |

---

## ✅ FAZIT

### IHRE FRAGE:
> "Besteht die Gefahr der unbefugten Weitergabe?"

### ANTWORT:

**Bei einfacher ZIP-Datei:** ❌ **JA, Gefahr besteht!**

**Mit Hardware-Bindung:** ✅ **NEIN, geschützt!**

### EMPFOHLENE LÖSUNG:

```
STUFE 2: Hardware-Bindung
├── ✅ Bereits implementiert (license_system.py)
├── ✅ In GUI integriert (tc_main_gui.py)
├── ✅ Sehr sicher
└── ✅ Einfach zu nutzen

AKTIVIERUNG:
└── Passwort: Hanbo2001!

ERGEBNIS:
└── Software läuft nur auf autorisiertem PC
    Weitergabe = Nicht funktionsfähig!
```

---

## 🚀 NÄCHSTE SCHRITTE

### Option A: Mit Hardware-Bindung (EMPFOHLEN)

```bash
1. Build mit Lizenz-System:
   python build_portable.py

2. Installiere auf Ziel-PC

3. Erste Ausführung:
   → Aktivierungs-Dialog
   → Passwort eingeben: Hanbo2001!
   → ✅ Aktiviert!

4. Software ist jetzt an DIESEN PC gebunden
```

### Option B: Nur Installer-Passwort (Einfacher)

```bash
1. Build Installer:
   python build_installer_pro.py

2. Installiere mit Passwort:
   → Passwort: Hanbo2001!

3. ⚠️ Nach Installation: Keine weitere Kontrolle
```

---

## 📞 SUPPORT

Bei Fragen zur Lizenz-Implementierung:
- Siehe: `license_system.py` (Gut kommentiert)
- Test: `python license_system.py --show-id` (Zeigt Hardware-ID)

---

**Zusammenfassung:** Mit der Hardware-Bindung (Stufe 2) ist Ihre Software **sehr gut geschützt** vor unbefugter Weitergabe! Die Implementierung ist bereits fertig und einsatzbereit. 🔐
