# KKT Kolbe EB8313HC Backofen - Data Points

Verifiziert von @Lucky-ESA (GitHub Issue #6), April 2026.

- **Product Key:** be8ooigdvjvy1q4a
- **Protocol Version:** 3.4
- **Tuya Category:** kfj (Backofen)
- **WiFi Module:** v2.7.7, MCU: v1.0.0

## Aktive Steuerungs-DPs (101-107)

| DP  | Code      | Name              | Typ   | Bereich           | Modus | Beschreibung |
|-----|-----------|-------------------|-------|-------------------|-------|--------------|
| 101 | dw        | Programm          | enum  | f1-f10, p1-p8     | rw    | Programm/Modus Auswahl |
| 102 | wd        | Temperatur        | value | 35-250°C, Step 5  | rw    | Zieltemperatur |
| 103 | ds        | Timer             | value | 0-360 min, Step 1 | rw    | Timer/Dauer einstellen |
| 104 | djs       | Restzeit          | value | 0-360 min         | ro    | Countdown (read-only) |
| 105 | kg        | Start/Cancel      | bool  | true/false        | rw    | true=Start, false=Cancel. Startet Programm mit Licht an. |
| 106 | ztjx      | Pause/Resume      | bool  | true/false        | rw    | false=Pause, true=Resume |
| 107 | doorstate | Tuerstatus        | bool  | true/false        | ro*   | Tuer auf/zu (*API sagt rw, Nutzer sagt read-only) |

## Preset-Default DPs (108-120)

Diese DPs speichern die Standardwerte fuer Temperatur und Zeit der Preset-Programme.

| DP  | Code | Preset              | Typ   | Bereich           |
|-----|------|----------------------|-------|-------------------|
| 108 | f3wd | Unterhitze Temp     | value | 35-200°C, Step 5  |
| 109 | p3wd | Pizza Temp          | value | 180-200°C, Step 5 |
| 110 | p3ds | Pizza Zeit          | value | 8-15 min          |
| 111 | p4wd | Unbekannt Temp      | value | 170-190°C, Step 5 |
| 112 | p4ds | Unbekannt Zeit      | value | 16-20 min         |
| 113 | p5wd | Huehnerschenkel Temp| value | 180-200°C, Step 5 |
| 114 | p5ds | Huehnerschenkel Zeit| value | 40-50 min         |
| 115 | p6wd | Unbekannt Temp      | value | 180-220°C, Step 5 |
| 116 | p6ds | Unbekannt Zeit      | value | 20-30 min         |
| 117 | p7wd | Kuchen Temp         | value | 190-210°C, Step 5 |
| 118 | p7ds | Kuchen Zeit         | value | 25-35 min         |
| 119 | p8wd | Rind Temp           | value | 175-190°C, Step 5 |
| 120 | p8ds | Rind Zeit           | value | 25-35 min         |

## Programme (DP 101)

### Manuelle Modi (f1-f10)

| Wert | Deutsch           | Englisch          |
|------|-------------------|-------------------|
| f1   | Auftaustufe       | Defrost           |
| f2   | Grossflaechengrill| Double Grill      |
| f3   | Unterhitze        | Bottom heat       |
| f4   | Pizzastufe        | Btm heat + Conv.  |
| f5   | Heissluft         | Convection        |
| f6   | Umluft            | Conventional + Fan|
| f7   | Ober/Unterhitze   | Conventional      |
| f8   | Grill/Bratsystem  | Dbl.grill + Fan   |
| f9   | Grill             | Grill             |
| f10  | Schnell-Aufheizen | Fast heat         |

### Preset-Programme (p1-p8)

| Wert | Deutsch           | Englisch     |
|------|-------------------|--------------|
| p1   | Aufwaermen        | Keep warm    |
| p2   | Toast             | Toast        |
| p3   | Pizza             | Pizza        |
| p4   | Unbekannt         | Unknown      |
| p5   | Huehnerschenkel   | Chicken Leg  |
| p6   | Unbekannt         | Unknown      |
| p7   | Kuchen            | Cake         |
| p8   | Rind              | Beef         |

## Hinweise

- **Kein Licht-DP**: Ofenlicht laesst sich nur ueber das Bedienfeld am Geraet steuern, nicht per App/Integration
- **Kein Kindersicherungs-DP**: Kindersicherung nicht ueber die App steuerbar
- **Kein Power-DP**: Es gibt keinen separaten Ein/Aus-Schalter. Start/Stop erfolgt ueber DP 105 (kg)
- **Kein Kerntemperaturfuehler**: Modell EB8313HC hat keinen (EB8313ED evtl. schon)
