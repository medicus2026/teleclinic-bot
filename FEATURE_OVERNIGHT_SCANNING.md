# 🌙 OVERNIGHT-SCANNING Feature

## ✅ Neue Funktion: Automatischer Filter-Wechsel bei Mitternacht

### Szenario
Sie starten den Scanner um 22:00 Uhr mit Filter "morgen":
- 22:00 - 23:59: Scanner läuft auf der **Morgen-Seite** (tab=1)
- 00:00 - 23:59: Scanner wechselt automatisch zur **Heute-Seite** (tab=0)

### Implementierte Logik

#### 1. **`check_and_update_day_window(filters, last_midnight_check)`**
   - Prüft ob Mitternacht überschritten wurde (Stunde < 4 Uhr)
   - Wechselt automatisch den `day_window` Filter:
     - `morgen` → `heute`
     - `später` → `morgen`
     - `heute` → `heute` (keine Änderung)
   - Loggt den Wechsel: `[MIDNIGHT] 🌙 Mitternacht überschritten! Wechsle Filter: morgen → heute`

#### 2. **Integration in die Hauptschleife**
   - Wird bei jedem Scan-Durchlauf aufgerufen
   - Prüfung nur alle 30 Sekunden (Performance-Optimierung)
   - Passt dynamisch die Browser-Navigation an

### Beispiel-Ablauf

```
22:00 Uhr - Start mit Filter "morgen"
├─ Scanner läuft auf: https://med.teleclinic.com/requests?tab=1&page=1 (Morgen-Seite)
├─ Scannung ...
└─ [SCAN] Scanne Seite 1 (tab=1)...

23:55 Uhr - Weiterhin auf Morgen-Seite
├─ Scanner läuft auf: https://med.teleclinic.com/requests?tab=1&page=1
└─ [SCAN] Scanne Seite 1 (tab=1)...

00:15 Uhr - MITTERNACHT ÜBERSCHRITTEN!
├─ [MIDNIGHT] 🌙 Mitternacht überschritten! Wechsle Filter: morgen → heute
├─ Scanner navigiert zu: https://med.teleclinic.com/requests?tab=0&page=1 (Heute-Seite)
└─ [SCAN] Scanne Seite 1 (tab=0)...

01:00 Uhr - Läuft weiterhin auf Heute-Seite
├─ Scanner läuft auf: https://med.teleclinic.com/requests?tab=0&page=1
└─ [SCAN] Scanne Seite 1 (tab=0)...
```

### Verwendung

Einfach den Scanner mit einem beliebigen Filter starten - der Overnight-Wechsel funktioniert automatisch!

**Beispiel:**
- Startet um 22:00 mit Filter "morgen" (14:00-15:30)
- Läuft über Nacht auf der Morgen-Seite
- Um 00:15 wechselt automatisch zur Heute-Seite
- Kann die ganze Nacht durchlaufen

### Technische Details

- **Prüffrequenz:** Alle 30 Sekunden (verhindert Performance-Probleme)
- **Erkennungsschwelle:** Stunde < 4 (berücksichtigt Zeitzonen-Variationen)
- **Filter-Wechsel:** Dynamisch, aktualisiert die laufende Scan-Session
- **Logging:** Alle Wechsel werden geloggt: `[MIDNIGHT] 🌙 ...`

### Zukünftige Erweiterungen

- Manuelle Konfiguration der Mitternacht-Zeit (für Zeitzonen)
- Automatisches Zurücksetzen von Scheduler-Slots bei Filter-Wechsel
- Benachrichtigung bei Filter-Wechsel (Email, SMS, etc.)

---

**Status:** ✅ Implementiert, getestet und produktionsreif

