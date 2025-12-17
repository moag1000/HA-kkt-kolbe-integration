# KKT Kolbe Blueprints

Fertige Automations-Vorlagen für deine KKT Kolbe Geräte.

## Installation

### Methode 1: Import-Button (empfohlen)

Klicke auf den Import-Button bei der gewünschten Blueprint:

| Blueprint | Beschreibung | Import |
|-----------|--------------|--------|
| [Hood Auto-Off](automation/hood_auto_off.yaml) | Schaltet Haube nach X Minuten aus | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_auto_off.yaml) |
| [Hood Light Auto-Off](automation/hood_light_auto_off.yaml) | Schaltet Licht nach X Minuten aus | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_light_auto_off.yaml) |
| [Hood with Cooktop (Erweitert)](automation/hood_with_cooktop.yaml) | Intelligente Synchronisation mit Kochfeld | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_with_cooktop.yaml) |

### Methode 2: Manuell

1. Kopiere die YAML-Datei nach `config/blueprints/automation/kkt_kolbe/`
2. Starte Home Assistant neu
3. Gehe zu Einstellungen → Automatisierungen → Blueprints

## Verfügbare Blueprints

### Dunstabzugshaube Auto-Aus
Schaltet die Dunstabzugshaube automatisch aus, wenn sie eine bestimmte Zeit lang gelaufen ist.

**Einstellungen:**
- Power-Entity der Haube
- Fan-Entity der Haube
- Timeout in Minuten (Standard: 60)
- Optionale Benachrichtigung vor dem Ausschalten

### Dunstabzugshaube Licht Auto-Aus
Schaltet das Licht der Dunstabzugshaube automatisch aus.

**Einstellungen:**
- Licht-Entity der Haube
- Timeout in Minuten (Standard: 30)

### Dunstabzugshaube mit Kochfeld synchronisieren (Erweitert)

**Die intelligenteste Art, deine Dunstabzugshaube zu steuern!**

Diese erweiterte Blueprint passt die Lüftergeschwindigkeit automatisch an den Stromverbrauch deines Kochfelds an. Je intensiver du kochst, desto stärker läuft der Lüfter.

**Features:**
- **Power-basierte Geschwindigkeit**: 4 Stufen (niedrig/mittel/hoch/boost) basierend auf Watt-Verbrauch
- **Gestufter Nachlauf**: Nach dem Kochen reduziert sich die Geschwindigkeit schrittweise
- **Automatische Lichtsteuerung**: Optional wird das Licht beim Kochen mitgeschaltet
- **Schnelle Reaktion**: Bei plötzlichem Power-Anstieg wird sofort hochgeregelt
- **Wiederkoch-Erkennung**: Wenn du während des Nachlaufs wieder anfängst zu kochen, startet die Automation neu

**Voraussetzungen:**
- Stromverbrauch-Sensor für das Kochfeld (z.B. Shelly Plug)
- KKT Kolbe Dunstabzugshaube

**Standardwerte (optimiert für typische Induktionskochfelder):**

| Schwellenwert | Leistung | Lüfter-Geschwindigkeit |
|---------------|----------|------------------------|
| Start | 50W | 25% |
| Mittel | 1000W | 50% |
| Hoch | 2500W | 75% |
| Boost | 5000W | 100% |

**Nachlauf-Stufen (Standard):**
1. **3 Minuten** auf mittlerer Stufe (50%)
2. **5 Minuten** auf niedriger Stufe (25%)
3. **5 Minuten** auf minimaler Stufe (25%)
4. Dann Abschaltung

**Einstellungen im Detail:**

| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| Kochfeld Stromverbrauch-Sensor | Sensor der den aktuellen Verbrauch misst | - |
| Start-Schwellenwert | Ab welchem Verbrauch startet die Haube? | 50W |
| Mittlere Leistung | Ab wann mittlere Stufe? | 1000W |
| Hohe Leistung | Ab wann hohe Stufe? | 2500W |
| Boost-Leistung | Ab wann maximale Stufe? | 5000W |
| Lüfter-Geschwindigkeiten | Für jede Stufe einstellbar | 25/50/75/100% |
| Gestufter Nachlauf | Schrittweise Reduzierung aktivieren | Ja |
| Nachlauf-Zeiten | Für jede Stufe einstellbar | 3/5/5 min |
| Licht einschalten | Automatisch Licht an beim Kochen | Ja |

## Weitere Beispiele

Für komplexere Automationen siehe [docs/AUTOMATION_EXAMPLES.md](../docs/AUTOMATION_EXAMPLES.md)
