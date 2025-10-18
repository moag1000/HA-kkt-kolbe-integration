# Datenpunkte (DPs) für KKT Kolbe IND7705HC Induktionskochfeld

## Gerätemodell Information
- **Modell-ID**: e1kc5q64
- **Kategorie**: Induktionskochfeld (cooktop)
- **Name**: IND7705HC Induction Cooktop
- **Produkt-ID**: p8volecsgzdyun29
- **Geräte-ID-Muster**: bf5592b47738c5b46e

## Grundstruktur

Das IND7705HC Induktionskochfeld verfügt über 5 Kochzonen und komplexe Steuerungsmöglichkeiten. Die Datenpunkte lassen sich in folgende Kategorien einteilen:

1. **Grundlegende Gerätesteuerung** (DPs 101-104, 108, 134, 145)
2. **Zoneneigenschaften** (DPs 162, 167-169)
3. **Zonenzustandssteuerung** (DPs 161, 163-166)
4. **Schnellwahlmodi** (DPs 148-152)
5. **Spezialfunktionen** (DPs 105-107, 153-155)

## Alle Datenpunkte im Detail

| DP-Nummer | Property Code | Datentyp | Beschreibung | Wertebereich |
|-----------|---------------|----------|-------------|--------------|
| 101 | user_device_power_switch | bool | Hauptschalter (Ein/Aus) | true/false |
| 102 | user_device_pause_switch | bool | Start/Pause-Funktion | true/false |
| 103 | user_device_lock_switch | bool | Kindersicherung | true/false |
| 104 | user_device_cur_max_level | value | Maximale Leistungsstufe | 0-25 |
| 105 | oem_hob_error_num | raw | Fehlercodes pro Zone (Bitfeld) | Bytearray, 1 Byte pro Zone |
| 106 | oem_device_chef_level | raw | Küchenchef-Funktion (Bitfeld) | Bytearray, 1 Byte pro Zone |
| 107 | oem_hob_bbq_timer | raw | BBQ-Timer (Bitfeld) | Bytearray, links/rechts |
| 108 | oem_device_confirm | bool | Bestätigungsaktion | true/false |
| 134 | oem_device_timer_num | value | Allgemeiner Timer | 0-99 min |
| 145 | oem_device_old_people | bool | Seniorenmodus | true/false |
| 148 | oem_hob_1_quick_level | enum | Zone 1 Schnellwahlstufe | set_quick_level_1 bis set_quick_level_5 |
| 149 | oem_hob_2_quick_level | enum | Zone 2 Schnellwahlstufe | set_quick_level_1 bis set_quick_level_5 |
| 150 | oem_hob_3_quick_level | enum | Zone 3 Schnellwahlstufe | set_quick_level_1 bis set_quick_level_5 |
| 151 | oem_hob_4_quick_level | enum | Zone 4 Schnellwahlstufe | set_quick_level_1 bis set_quick_level_5 |
| 152 | oem_hob_5_quick_level | enum | Zone 5 Schnellwahlstufe | set_quick_level_1 bis set_quick_level_5 |
| 153 | oem_device_save_level | enum | Zonenstufe speichern | save_hob1 bis save_hob5 |
| 154 | oem_device_set_level | enum | Zonenstufe einstellen | set_hob1 bis set_hob5 |
| 155 | oem_device_power_limit | enum | Leistungsbegrenzung | power_limit_1 bis power_limit_5 |
| 161 | oem_hob_selected_switch | raw | Zonenauswahl (Bitfeld) | Bit 0-4 für Zonen 1-5 |
| 162 | oem_hob_level_num | raw | Zonenleistungsstufen (Bitfeld) | Bytearray, 1 Byte pro Zone (0-25) |
| 163 | oem_hob_boost_switch | raw | Boost-Modus pro Zone (Bitfeld) | Bit 0-4 für Zonen 1-5 |
| 164 | oem_hob_warm_switch | raw | Warmhaltefunktion pro Zone (Bitfeld) | Bit 0-4 für Zonen 1-5 |
| 165 | oem_hob_flex_switch | raw | Flexzone (Bitfeld) | Bit 0 für links, Bit 1 für rechts |
| 166 | oem_hob_bbq_switch | raw | BBQ-Modus (Bitfeld) | Bit 0 für links, Bit 1 für rechts |
| 167 | oem_hob_timer_num | raw | Timer pro Zone (Bitfeld) | Bytearray, 1 Byte pro Zone (0-255 min) |
| 168 | oem_hob_set_core_sensor | raw | Kerntemperatursensor (Bitfeld) | Bytearray, 1 Byte pro Zone (0-300°C) |
| 169 | oem_hob_disp_coresensor | raw | Anzeige Kerntemperatur (Bitfeld) | Bytearray, 1 Byte pro Zone (0-300°C) |

## Bitfeld-Datenpunkte im Detail

### DP 105 - Fehlercodes pro Zone (oem_hob_error_num)
Speichert Fehlercodes für jede Kochzone in einem Bytearray:
- Byte 0: Fehlercode Zone 1
- Byte 1: Fehlercode Zone 2
- Byte 2: Fehlercode Zone 3
- Byte 3: Fehlercode Zone 4
- Byte 4: Fehlercode Zone 5

### DP 161 - Zonenauswahl (oem_hob_selected_switch)
Ein einzelnes Byte, bei dem jedes Bit den Auswahlzustand einer Zone repräsentiert:
- Bit 0: Zone 1 ausgewählt (ja/nein)
- Bit 1: Zone 2 ausgewählt (ja/nein)
- Bit 2: Zone 3 ausgewählt (ja/nein)
- Bit 3: Zone 4 ausgewählt (ja/nein)
- Bit 4: Zone 5 ausgewählt (ja/nein)

### DP 162 - Zonenleistungsstufen (oem_hob_level_num)
Speichert die Leistungsstufen (0-25) für jede Kochzone in einem Bytearray:
- Byte 0: Leistungsstufe Zone 1
- Byte 1: Leistungsstufe Zone 2
- Byte 2: Leistungsstufe Zone 3
- Byte 3: Leistungsstufe Zone 4
- Byte 4: Leistungsstufe Zone 5

### DP 163 - Boost-Modus pro Zone (oem_hob_boost_switch)
Ein einzelnes Byte, bei dem jedes Bit den Boost-Status einer Zone repräsentiert:
- Bit 0: Zone 1 Boost aktiv (ja/nein)
- Bit 1: Zone 2 Boost aktiv (ja/nein)
- Bit 2: Zone 3 Boost aktiv (ja/nein)
- Bit 3: Zone 4 Boost aktiv (ja/nein)
- Bit 4: Zone 5 Boost aktiv (ja/nein)

### DP 164 - Warmhaltefunktion pro Zone (oem_hob_warm_switch)
Ein einzelnes Byte, bei dem jedes Bit den Warmhaltestatus einer Zone repräsentiert:
- Bit 0: Zone 1 Warmhalten aktiv (ja/nein)
- Bit 1: Zone 2 Warmhalten aktiv (ja/nein)
- Bit 2: Zone 3 Warmhalten aktiv (ja/nein)
- Bit 3: Zone 4 Warmhalten aktiv (ja/nein)
- Bit 4: Zone 5 Warmhalten aktiv (ja/nein)

### DP 165 - Flexzone (oem_hob_flex_switch)
Ein einzelnes Byte, das den Status der Flexzonen repräsentiert:
- Bit 0: Linke Flexzone aktiv (ja/nein)
- Bit 1: Rechte Flexzone aktiv (ja/nein)

### DP 166 - BBQ-Modus (oem_hob_bbq_switch)
Ein einzelnes Byte, das den BBQ-Modus für die linke und rechte Seite repräsentiert:
- Bit 0: Linker BBQ-Modus aktiv (ja/nein)
- Bit 1: Rechter BBQ-Modus aktiv (ja/nein)

### DP 167 - Timer pro Zone (oem_hob_timer_num)
Speichert die Timer-Einstellungen für jede Kochzone in einem Bytearray:
- Byte 0: Timer Zone 1 (0-255 min)
- Byte 1: Timer Zone 2 (0-255 min)
- Byte 2: Timer Zone 3 (0-255 min)
- Byte 3: Timer Zone 4 (0-255 min)
- Byte 4: Timer Zone 5 (0-255 min)

### DP 168 - Kerntemperatursensor (oem_hob_set_core_sensor)
Speichert die eingestellten Kerntemperaturen für jede Kochzone in einem Bytearray:
- Byte 0: Kerntemperatur Zone 1 (0-300°C)
- Byte 1: Kerntemperatur Zone 2 (0-300°C)
- Byte 2: Kerntemperatur Zone 3 (0-300°C)
- Byte 3: Kerntemperatur Zone 4 (0-300°C)
- Byte 4: Kerntemperatur Zone 5 (0-300°C)

### DP 169 - Anzeige Kerntemperatur (oem_hob_disp_coresensor)
Speichert die angezeigten Kerntemperaturen für jede Kochzone in einem Bytearray:
- Byte 0: Angezeigte Kerntemperatur Zone 1 (0-300°C)
- Byte 1: Angezeigte Kerntemperatur Zone 2 (0-300°C)
- Byte 2: Angezeigte Kerntemperatur Zone 3 (0-300°C)
- Byte 3: Angezeigte Kerntemperatur Zone 4 (0-300°C)
- Byte 4: Angezeigte Kerntemperatur Zone 5 (0-300°C)

## Implementierung im Home Assistant

Das IND7705HC Kochfeld wird in Home Assistant mit folgenden Entitätstypen integriert:

1. **Schalter (switch)**: Hauptschalter, Pause, Kindersicherung, Seniorenmodus, Bestätigungsaktion
2. **Zahlenwerte (number)**: Maximale Leistungsstufe, Allgemeiner Timer, Zonenleistungen (1-5), Zonentimer (1-5), Zonenkerntemperaturen (1-5)
3. **Auswahlmenüs (select)**: Zonenschnellwahlstufen (1-5), Zonenspeichern, Zoneneinstellen, Leistungsbegrenzung
4. **Sensoren (sensor)**: Zonenfehler (1-5), Anzeige Kerntemperaturen (1-5)
5. **Binäre Sensoren (binary_sensor)**: Zonenauswahl (1-5), Zonenboost (1-5), Zonenwarmhalten (1-5), Flexzone (links/rechts), BBQ-Modus (links/rechts)

## Hinweise zur Datenpunktnutzung

1. **Bitfeld-Verarbeitung**: Viele Datenpunkte verwenden Bitfelder oder Bytearrays zur effizienten Speicherung von Daten für alle Zonen. Die Integration muss diese korrekt dekodieren und enkodieren.

2. **Raw-Datentypen**: Datenpunkte mit dem Typ "raw" werden als Bytearray oder Bitfelder verarbeitet und benötigen spezielle Handhabung in der Integration.

3. **Zonenspezifische Operationen**: Die meisten Operationen sind zonenbezogen, wobei ein einzelner Datenpunkt (z.B. DP 162) Daten für alle 5 Zonen enthält.

4. **Flexzone-Funktion**: Die Flexzone-Funktion (DP 165) ermöglicht es, benachbarte Zonen zu kombinieren für größere Kochflächen.

5. **BBQ-Modus**: Der BBQ-Modus (DP 166) ist eine Spezialfunktion für gleichmäßiges Grillen auf mehreren Zonen.