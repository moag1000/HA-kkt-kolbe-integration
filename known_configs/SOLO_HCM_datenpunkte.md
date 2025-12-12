# Datenpunkte (DPs) für KKT Kolbe SOLO HCM Dunstabzugshaube

## Geräte-Informationen

- **Modell**: KKT Kolbe SOLO HCM
- **Produkt-ID**: bgvbvjwomgbisd8x
- **Device-ID**: bf34515c4ab6ec7f9axqy8
- **Kategorie**: yyj (Dunstabzugshaube)
- **Produktseite**: https://www.kolbe.de/Dunstabzugshaube-60cm-SOLO6005S

## Technische Spezifikationen (laut Hersteller)

- **Lüfterstufen**: 9 Stufen (272-782 m³/h)
- **Beleuchtung**: Weiße LED (2x1,5W) - **KEIN RGB**
- **Energieeffizienzklasse**: A+++
- **Schallleistungspegel**: 65 dB
- **Nachlaufautomatik**: Ja
- **Betriebsart**: Abluft oder Umluft

## Alle definierten Datenpunkte

Die folgende Tabelle zeigt alle Datenpunkte (DPs), die für dieses Gerätemodell erwartet werden (basierend auf HERMES-Struktur):

| DP-Nummer | Property Code | Beschreibung | Erwartet aktiv |
|-----------|---------------|-------------|----------------|
| 1 | switch | Hauptschalter (Ein/Aus) | Ja |
| 2 | delay_switch | Verzögerte Abschaltung (Nachlauf) | Unklar |
| 4 | light | Beleuchtung ein/aus | Ja |
| 5 | light_brightness | Helligkeit der Beleuchtung (0-255) | Unklar |
| 6 | switch_lamp | Filterreinigungserinnerung | Ja |
| 7 | switch_wash | Reinigungsmodus | Unklar |
| 10 | fan_speed_enum | Lüftergeschwindigkeit (Enum: off, low, middle, high, strong) | Ja |
| 13 | countdown | Timer (0-60 Min) | Ja |
| 14 | filter_hours | Filternutzungsstunden | Unklar |
| 15 | filter_reset | Filter zurücksetzen | Unklar |
| 17 | eco_mode | Eco-Modus ein/aus | Unklar |

## Unterschiede zur HERMES & STYLE

| Feature | SOLO HCM | HERMES & STYLE |
|---------|----------|----------------|
| RGB Beleuchtung | **Nein** | Ja (DP 101) |
| RGB Helligkeit | **Nein** | Ja (DP 102) |
| Farbtemperatur | **Nein** | Ja (DP 103) |
| Lüfterstufen | 9 (mapped to 5) | 5 |
| LED Typ | Weiß (2x1,5W) | RGB |

## Erwartete aktive Datenpunkte

Basierend auf der Produktbeschreibung und der HERMES-Struktur werden folgende DPs als aktiv erwartet:

1. **DP 1: switch** - Hauptschalter ✅
2. **DP 4: light** - Beleuchtung ✅
3. **DP 6: switch_lamp** - Filterreinigungserinnerung ✅
4. **DP 10: fan_speed_enum** - Lüftergeschwindigkeit ✅
5. **DP 13: countdown** - Timer ✅

## Experimentelle Datenpunkte

Die folgenden DPs könnten funktionieren, sind aber als **"disabled by default"** verfügbar:

1. **DP 2: delay_switch** - Nachlaufautomatik 🧪
2. **DP 5: light_brightness** - Helligkeitssteuerung (0-255) 🧪
3. **DP 7: switch_wash** - Reinigungsmodus 🧪
4. **DP 14: filter_hours** - Filternutzungsstunden 🧪
5. **DP 15: filter_reset** - Filter-Zähler zurücksetzen 🧪
6. **DP 17: eco_mode** - Eco-Modus 🧪

**Aktivierung:** Diese experimentellen Entities müssen manuell in Home Assistant aktiviert werden:
- Einstellungen → Geräte & Dienste → KKT Kolbe → Gerät auswählen
- "X disabled entities" → Entity auswählen → Enable

## Hinweise

- **WICHTIG**: Diese Konfiguration basiert auf Annahmen und der HERMES-Struktur
- Das tatsächliche "Things Data Model" von Tuya wird benötigt, um die exakten DPs zu bestätigen
- Die 9 physischen Lüfterstufen werden auf 5 Enum-Werte gemappt (off/low/middle/high/strong)
- Keine RGB-Unterstützung - nur weiße LED-Beleuchtung

## Tuya API Daten (von Nutzer geliefert)

### Device Details
```json
{
  "result": {
    "id": "bf34515c4ab6ec7f9axqy8",
    "product_id": "bgvbvjwomgbisd8x",
    "product_name": "KKT Kolbe SOLO HCM",
    "model": "SOLO HCM",
    "category": "yyj",
    "is_online": true
  }
}
```

### Get instruction set (unvollständig - nur 4 Standard-DPs)
```json
{
  "functions": [
    {"code": "switch", "type": "Boolean"},
    {"code": "light", "type": "Boolean"},
    {"code": "switch_lamp", "type": "Boolean"},
    {"code": "switch_wash", "type": "Boolean"}
  ]
}
```

**ACHTUNG**: Diese 4 DPs sind nur die Standard-Boolean-Funktionen. Das vollständige "Things Data Model" sollte weitere DPs wie `fan_speed_enum` und `countdown` enthalten!
