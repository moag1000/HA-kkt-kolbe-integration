# Datenpunkte (DPs) für KKT Kolbe ECCO HCM Dunstabzugshaube

## Gerätemodell Information
- **Modell-ID**: edjsx0
- **Kategorie**: Dunstabzugshaube (hood)
- **Name**: KKT Kolbe ECCO HCM Hood
- **Produkt-ID**: gwdgkteknzvsattn (laut device_types.py)
- **Geräte-ID-Muster**: bfd0c94cb36bf4f28e (laut device_types.py)

## Grundlegende Eigenschaften

Die KKT Kolbe ECCO HCM Dunstabzugshaube ist mit 12 Datenpunkten (DPs) ausgestattet, die eine Vielzahl von Funktionen bieten, darunter Hauptschalter, Beleuchtung, Lüftersteuerung, RGB-Licht und Timer-Funktionen. Alle Datenpunkte haben Lese- und Schreibzugriff (accessMode: "rw").

## Alle Datenpunkte im Detail

| DP-Nummer | Property Code | Datentyp | Beschreibung | Wertebereich |
|-----------|---------------|----------|-------------|--------------|
| 1 | switch | bool | Hauptschalter (Ein/Aus) | true/false |
| 4 | light | bool | Hauptbeleuchtung ein/aus | true/false |
| 6 | switch_lamp | bool | RGB-Licht-Schalter/Trigger | true/false |
| 7 | switch_wash | bool | Einstellungs-/Waschfunktion | true/false |
| 102 | fan_speed | value | Lüftergeschwindigkeit | 0-9 |
| 103 | day | value | Aktivkohlefilter-Tage | 0-250 Tage |
| 104 | switch_led_1 | bool | LED-Beleuchtung | true/false |
| 105 | countdown_1 | value | Countdown-Timer | 0-60 min |
| 106 | switch_led | bool | Bestätigungsfunktion | true/false |
| 107 | colour_data | string | RGB-Farbdaten (Hex-String) | String (max 255 Zeichen) |
| 108 | work_mode | enum | RGB-Arbeitsmodus | white, colour, scene, music |
| 109 | day_1 | value | Metallfilter-Reinigungstage | 0-40 Tage |

## Funktionsgruppen

Die Datenpunkte lassen sich in folgende Funktionsgruppen einteilen:

### 1. Grundlegende Gerätesteuerung
- **DP 1**: Hauptschalter für Ein/Aus
- **DP 7**: Einstellungs-/Waschfunktion
- **DP 106**: Bestätigungsfunktion

### 2. Beleuchtungssystem
- **DP 4**: Hauptbeleuchtung
- **DP 104**: LED-Beleuchtung 
- **DP 6**: RGB-Licht-Schalter/Trigger

### 3. RGB-Beleuchtungssteuerung
- **DP 107**: RGB-Farbdaten (Hex-String für Farbwerte)
- **DP 108**: RGB-Arbeitsmodus (weiß, farbe, szene, musik)

### 4. Lüftersteuerung
- **DP 102**: Lüftergeschwindigkeit (0-9 Stufen)

### 5. Timer und Wartung
- **DP 105**: Countdown-Timer (0-60 min)
- **DP 103**: Aktivkohlefilter-Wartungszähler (0-250 Tage)
- **DP 109**: Metallfilter-Wartungszähler (0-40 Tage)

## Besonderheiten und Implementierungshinweise

### RGB-Beleuchtung
Die RGB-Beleuchtung der ECCO HCM bietet erweiterte Funktionalität im Vergleich zu anderen KKT Kolbe Modellen:
- Unterstützung für verschiedene Arbeitsmodi (weiß, farbe, szene, musik)
- Direkte Steuerung der RGB-Farbe über Hex-Strings
- Separater Trigger für RGB-Beleuchtung (switch_lamp)

### Filterwartung
Das Gerät bietet zwei separate Filterwartungssysteme:
- Aktivkohlefilter mit längerer Wartungsperiode (bis zu 250 Tage)
- Metallfilter mit kürzerer Wartungsperiode (bis zu 40 Tage)

### Implementierung im Home Assistant
Das Gerät wird in Home Assistant mit folgenden Entitätstypen integriert:
1. **Fan**: Lüftersteuerung mit 10 Geschwindigkeitsstufen (0-9)
2. **Light**: Hauptbeleuchtung, LED-Beleuchtung und RGB-Beleuchtung
3. **Switch**: Hauptschalter, RGB-Schalter, Wash-Modus, Bestätigung
4. **Number**: Countdown-Timer, Aktivkohlefilter-Reset, Metallfilter-Reset
5. **Select**: RGB-Arbeitsmodus
6. **Sensor**: Filternutzungsstände

## Vergleich mit anderen KKT Kolbe Modellen

Im Vergleich zum HERMES & STYLE Modell bietet die ECCO HCM:
- Erweiterte RGB-Beleuchtungsfunktionen (verschiedene Modi, direkter Farbzugriff)
- Detaillierteres Filterwartungssystem mit zwei separaten Filtern
- Eine einfachere Lüftersteuerung mit direkter Geschwindigkeitseinstellung (0-9) statt enum-Werten

## Hinweise

- Die RGB-Farbsteuerung verwendet ein spezielles String-Format zur Übertragung von Farbinformationen
- Die Filterwartungstage können zurückgesetzt werden, indem der entsprechende Wert auf 0 gesetzt wird
- Der Arbeitsmodus "music" deutet auf eine mögliche Musiksynchronisationsfunktion hin, die vom Steuergerät unterstützt wird