# 🛡️ Hybrid Tag-Filter System - Dokumentation

## Übersicht

Der TeleClinic Bot verwendet jetzt einen **Hybrid-Ansatz** für maximale Stabilität beim Setzen des Tag-Filters (Heute/Morgen/Später).

## Wie es funktioniert

### 1️⃣ PRIMÄR-METHODE: URL-Navigation
- **Schnell & effizient**
- Verwendet URL-Parameter: `?tab=0` (Heute), `?tab=1` (Morgen), `?tab=2` (Später)
- Direkter Zugriff ohne DOM-Interaktion

```
Heute:  https://med.teleclinic.com/requests?tab=0&page=1
Morgen: https://med.teleclinic.com/requests?tab=1&page=1
Später: https://med.teleclinic.com/requests?tab=2&page=1
```

### 2️⃣ VALIDIERUNG: Button-Text prüfen
- Prüft nach Navigation den Button-Text via `data-testid="filter-date"`
- Stellt sicher, dass der Filter wirklich gesetzt ist
- Erkennt, wenn URL-Methode nicht mehr funktioniert

### 3️⃣ FALLBACK: Button-Klick
- **Nur wenn Validierung fehlschlägt**
- Klickt automatisch den Datumsfilter-Button
- Wählt richtigen Menüeintrag (Heute/Morgen/Später)
- Selbstheilend bei TeleClinic-Änderungen

## Vorteile

✅ **Zukunftssicher**: Funktioniert auch wenn TeleClinic URL-Struktur ändert
✅ **Selbstheilend**: Erkennt automatisch, wenn URL-Methode nicht mehr klappt
✅ **Performance**: URL-Methode ist schnell, Fallback nur bei Bedarf
✅ **Transparenz**: Detailliertes Logging zeigt verwendete Methode
✅ **Zuverlässig**: Doppelte Absicherung (URL + Button)

## Log-Einträge

### Normal (URL funktioniert):
```
[INFO] 🗓️ Tag-Filter: Morgen (Methode: URL tab=1 + Validierung)
[FILTER] Validierung: Button zeigt 'Morgen', erwartet 'Morgen'
[FILTER] ✅ Datumsfilter korrekt: 'Morgen'
```

### Fallback (URL funktioniert nicht mehr):
```
[INFO] 🗓️ Tag-Filter: Morgen (Methode: URL tab=1 + Validierung)
[FILTER] Validierung: Button zeigt 'Heute', erwartet 'Morgen'
[FILTER] ⚠️ URL-Tab-Methode funktioniert nicht! Fallback auf Button-Klick...
[FILTER] Suche 'Morgen' in 3 Menüeinträgen...
[FILTER] ✓ Gefunden: 'Morgen'
[FILTER] ✅ Button-Klick erfolgreich: 'Morgen'
```

## Wartung

- **Keine manuelle Anpassung nötig**: System wählt automatisch beste Methode
- **Bei TeleClinic-Änderungen**: Fallback aktiviert sich automatisch
- **Monitoring**: Prüfe Logs auf "Fallback"-Warnungen

## Technische Details

### Funktionen
- `get_tab_number(day_window)`: Konvertiert "heute"/"morgen"/"später" → tab-Nummer
- `validate_and_fix_day_filter(page, day_window)`: Validierung + Fallback-Logik

### Integration
- **Startup**: Einmalige Validierung beim Bot-Start
- **Scan-Loop**: Validierung vor jeder ersten Seite (page=1)
- **Jeder Scan**: URL-Navigation mit korrektem tab-Parameter

## Datum: 2026-01-25
Implementiert in: `teleclinic_click_from_list_v9d.py`
Version: Hybrid 1.0
