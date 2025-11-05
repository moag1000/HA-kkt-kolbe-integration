# Datenpunkte (DPs) für KKT Kolbe HERMES & STYLE Dunstabzugshaube

## Alle definierten Datenpunkte

Die folgende Tabelle zeigt alle Datenpunkte (DPs), die für dieses Gerätemodell definiert sind:

| DP-Nummer | Property Code | Beschreibung | Im aktuellen Gerät aktiv |
|-----------|---------------|-------------|--------------------------|
| 1 | switch | Hauptschalter (Ein/Aus) | Ja |
| 2 | delay_switch | Verzögerte Abschaltung | Nein |
| 3 | auto_mode | Automatikmodus ein/aus | Nein |
| 4 | light | Beleuchtung ein/aus | Ja |
| 5 | light_brightness | Helligkeit der Beleuchtung (0-255) | Nein |
| 6 | switch_lamp | Filterreinigungserinnerung | Ja |
| 7 | temperature | Temperatursensor | Nein |
| 8 | humidity | Feuchtigkeitssensor | Nein |
| 9 | air_quality | Luftqualitätssensor | Nein |
| 10 | fan_speed_enum | Lüftergeschwindigkeit (Enum: off, low, middle, high, strong) | Ja |
| 11 | fan_speed_set | Direkte Lüftergeschwindigkeitseinstellung (0-4) | Nein |
| 12 | auto_clean | Automatischer Reinigungsmodus | Nein |
| 13 | countdown | Timer (0-60 Min) | Ja |
| 14 | filter_hours | Filternutzungsstunden | Nein |
| 15 | filter_reset | Filter zurücksetzen | Nein |
| 16 | noise_level | Geräuschpegeleinstellung | Nein |
| 17 | eco_mode | Eco-Modus ein/aus | Nein |
| 101 | RGB | RGB-Lichtmodus (0-9) | Ja |
| 102 | rgb_brightness | RGB-Helligkeit (0-255) | Nein |
| 103 | color_temp | Farbtemperatur (warm/kalt) | Nein |

## Aktive Datenpunkte im aktuellen Gerät

Basierend auf dem Datenmodell vom Tuya IoT Portal (API v2.0 Things Data Model) sind derzeit nur folgende DPs im Gerät aktiv:

1. **DP 1: switch** - Hauptschalter ✅
2. **DP 4: light** - Beleuchtung ✅
3. **DP 6: switch_lamp** - Filterreinigungserinnerung ✅
4. **DP 10: fan_speed_enum** - Lüftergeschwindigkeit ✅
5. **DP 13: countdown** - Timer ✅
6. **DP 101: RGB** - RGB-Lichtmodus ✅

## Experimentelle Datenpunkte (v2.2.4+)

Die folgenden DPs wurden aus der API v2.0 Things Data Model extrahiert und sind als **"disabled by default"** verfügbar. Sie könnten bei manchen HERMES & STYLE Varianten oder nach Firmware-Updates funktionieren:

1. **DP 2: delay_switch** - Verzögerte Abschaltung (Nachlauf) 🧪
2. **DP 5: light_brightness** - Helligkeitssteuerung (0-255) 🧪
3. **DP 14: filter_hours** - Filternutzungsstunden 🧪
4. **DP 15: filter_reset** - Filter-Zähler zurücksetzen 🧪
5. **DP 17: eco_mode** - Eco-Modus 🧪
6. **DP 102: rgb_brightness** - RGB-Helligkeit (0-255) 🧪
7. **DP 103: color_temp** - Farbtemperatur (warm/neutral/cold) 🧪

**Aktivierung:** Diese experimentellen Entities müssen manuell in Home Assistant aktiviert werden:
- Einstellungen → Geräte & Dienste → KKT Kolbe → Gerät auswählen
- "X disabled entities" → Entity auswählen → Enable

## Hinweise

- Die Integration unterstützt technisch alle definierten DPs
- **Nur die 6 aktiven DPs** (✅) sind garantiert funktional
- **Experimentelle DPs** (🧪) könnten nicht funktionieren oder zu Fehlern führen
- Nicht aktive DPs könnten in zukünftigen Firmware-Updates aktiviert werden
- Verschiedene Varianten der HERMES & STYLE Dunstabzugshaube könnten unterschiedliche aktive DPs haben
- Bei Problemen mit experimentellen DPs: Einfach wieder deaktivieren