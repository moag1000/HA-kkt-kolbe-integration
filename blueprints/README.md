# KKT Kolbe Blueprints

Fertige Automations-Vorlagen für deine KKT Kolbe Geräte - durchdacht und praxisnah.

## Installation

### Methode 1: Import-Button (empfohlen)

Klicke auf den Import-Button bei der gewünschten Blueprint:

| Blueprint | Beschreibung | Import |
|-----------|--------------|--------|
| [Hood Auto-Off](automation/hood_auto_off.yaml) | Intelligente Auto-Abschaltung | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_auto_off.yaml) |
| [Hood Light Auto-Off](automation/hood_light_auto_off.yaml) | Licht intelligent ausschalten | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_light_auto_off.yaml) |
| [Hood with Cooktop](automation/hood_with_cooktop.yaml) | Kochfeld-Sync (externer Sensor) | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_with_cooktop.yaml) |
| [Hood with IND Cooktop](automation/hood_with_ind_cooktop.yaml) | **NEU!** Für KKT IND7705HC | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_with_ind_cooktop.yaml) |

### Methode 2: Manuell

1. Kopiere die YAML-Datei nach `config/blueprints/automation/kkt_kolbe/`
2. Starte Home Assistant neu
3. Gehe zu Einstellungen → Automatisierungen → Blueprints

---

## Dunstabzugshaube Auto-Aus (Erweitert)

Schaltet die Dunstabzugshaube automatisch aus mit intelligenten Features.

### Features
- **Gestuftes Herunterfahren** - Reduziert Geschwindigkeit schrittweise (schonender für Motor)
- **Timer-Reset bei Aktivität** - Geschwindigkeitsänderung verlängert die Laufzeit
- **Vorwarnung** - Benachrichtigung X Minuten vor dem Ausschalten
- **Actionable Notification** - "+30 Min" Button in der Benachrichtigung
- **Licht-Steuerung** - Optional Licht mit ausschalten
- **Lüfter-Check** - Nur ausschalten wenn Lüfter tatsächlich läuft

### Einstellungen

| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| Timeout | Nach wie vielen Minuten ausschalten? | 60 min |
| Timer bei Aktivität zurücksetzen | Neustart bei Geschwindigkeitsänderung | Ja |
| Gestuftes Herunterfahren | Schrittweise Reduzierung | Ja |
| Zeit pro Stufe | Dauer auf jeder Stufe | 30 s |
| Vorwarnzeit | Benachrichtigung X Min vorher | 2 min |

---

## Dunstabzugshaube Licht Auto-Aus (Erweitert)

Schaltet das Licht der Dunstabzugshaube intelligent aus.

### Features
- **Lüfter-Abhängigkeit** - Licht bleibt an solange Lüfter läuft
- **Bewegungsmelder-Integration** - Timer-Reset bei Bewegung in der Küche
- **Dimm-Warnung** - Reduziert Helligkeit vor dem Ausschalten
- **RGB-Effekt-Warnung** - Wechselt auf Rot/Orange als visuelle Warnung
- **Kürzerer Timeout nach Lüfter-Aus** - Schnellere Abschaltung wenn Kochen beendet

### Einstellungen

| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| Timeout | Nach wie vielen Minuten ausschalten? | 30 min |
| Timeout wenn Lüfter aus | Kürzerer Timeout nach Kochen | 5 min |
| Nur wenn Lüfter aus | Licht bleibt beim Kochen an | Nein |
| Dimmen vor Aus | Helligkeit reduzieren als Warnung | Nein |
| Effekt-Warnung | RGB auf Rot wechseln | Nein |

---

## Dunstabzugshaube mit Kochfeld synchronisieren (Erweitert)

**Die intelligenteste Art, deine Dunstabzugshaube zu steuern!**

Diese Blueprint passt die Lüftergeschwindigkeit automatisch an den Stromverbrauch deines Kochfelds an.

### Features
- **4 Power-Stufen** - Geschwindigkeit passt sich der Kochintensität an
- **Hysterese** - Verhindert ständiges Umschalten bei schwankendem Verbrauch
- **Startverzögerung** - Keine Fehlstarts bei kurzen Power-Spitzen
- **Mindestzeit pro Stufe** - Kein hektisches Hin- und Herschalten
- **Gestufter Nachlauf** - Schrittweise Reduzierung nach dem Kochen
- **Wiederkoch-Erkennung** - Startet neu wenn während Nachlauf wieder gekocht wird
- **Benachrichtigungen** - Optional bei Start/Stop/Ende
- **Licht-Steuerung** - Automatisch an beim Kochen, optional während Nachlauf

### Voraussetzungen
- **Stromverbrauch-Sensor** für das Kochfeld (z.B. Shelly Plug)
- KKT Kolbe Dunstabzugshaube

### Power-Schwellenwerte (Standardwerte)

| Schwellenwert | Leistung | Lüfter | Typische Verwendung |
|---------------|----------|--------|---------------------|
| Start | 50W | 25% | Aufwärmen, Simmern |
| Mittel | 1000W | 50% | Normales Kochen, Braten |
| Hoch | 2500W | 75% | Scharfes Anbraten |
| Boost | 5000W | 100% | Wok, mehrere Platten Vollgas |

### Hysterese & Stabilität

| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| Hysterese | Mindest-Differenz vor Stufenwechsel | 150W |
| Mindestzeit pro Stufe | Minimale Laufzeit auf einer Stufe | 30s |
| Startverzögerung | Verzögerung vor Einschalten | 5s |

### Nachlauf-Stufen (Standard)

```
Kochen beendet
    ↓
┌─────────────────────────────────┐
│ 3 Min auf mittlerer Stufe (50%) │  ← Restgerüche abziehen
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 5 Min auf niedriger Stufe (25%) │  ← Nachlüften
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│ 5 Min auf minimaler Stufe (25%) │  ← Sanftes Auslaufen
└─────────────────────────────────┘
    ↓
   AUS
```

### Alle Einstellungen

| Kategorie | Einstellung | Standard |
|-----------|-------------|----------|
| **Schwellenwerte** | Start-Schwellenwert | 50W |
| | Mittlere Leistung | 1000W |
| | Hohe Leistung | 2500W |
| | Boost-Leistung | 5000W |
| **Geschwindigkeiten** | Niedrig | 25% |
| | Mittel | 50% |
| | Hoch | 75% |
| | Boost | 100% |
| **Stabilität** | Hysterese | 150W |
| | Mindestzeit pro Stufe | 30s |
| | Startverzögerung | 5s |
| **Nachlauf** | Gestufter Nachlauf | Ja |
| | Nachlauf Stufe 1 (mittel) | 3 min |
| | Nachlauf Stufe 2 (niedrig) | 5 min |
| | Nachlauf Stufe 3 (minimal) | 5 min |
| **Licht** | Beim Kochen einschalten | Ja |
| | Während Nachlauf anlassen | Ja |
| **Benachrichtigungen** | Senden | Nein |

---

## Dunstabzugshaube mit KKT IND Kochfeld (NEU!)

**Speziell für das KKT Kolbe IND7705HC Induktionskochfeld!**

Diese Blueprint funktioniert **ohne externen Stromzähler** und nutzt stattdessen die integrierten Sensoren der IND7705HC:

### Verfügbare Sensoren

| Sensor | Beschreibung | Wertebereich |
|--------|--------------|--------------|
| **Estimated Power** | Geschätzter Stromverbrauch | 0-12500W |
| **Total Power Level** | Summe aller Zonen-Levels | 0-125 |
| **Active Zones** | Anzahl aktiver Kochzonen | 0-5 |

### Welchen Sensor wählen?

- **Estimated Power** (empfohlen): Arbeitet wie ein echter Stromzähler, kompatibel mit der Standard-Blueprint
- **Total Power Level**: Feiner abgestuft, berücksichtigt Intensität pro Zone
- **Active Zones**: Einfach, basiert nur auf Anzahl aktiver Zonen

### Standardwerte

**Für Estimated Power (Watt):**
| Schwelle | Wert | Lüfter |
|----------|------|--------|
| Start | 100W | 25% |
| Mittel | 500W | 50% |
| Hoch | 1500W | 75% |
| Boost | 3000W | 100% |

**Für Total Level (0-125):**
| Schwelle | Wert | Beispiel |
|----------|------|----------|
| Start | 1 | 1 Zone auf Stufe 1 |
| Mittel | 10 | 1 Zone auf 10 oder 2 Zonen auf 5 |
| Hoch | 30 | 2 Zonen auf 15 |
| Boost | 60 | 3 Zonen auf 20 |

**Für Active Zones (0-5):**
| Schwelle | Zonen | Lüfter |
|----------|-------|--------|
| Start | 1 | 25% |
| Mittel | 2 | 50% |
| Hoch | 3 | 75% |
| Boost | 4+ | 100% |

### Hinweis zur Genauigkeit

Die "Estimated Power" basiert auf der Formel: `Power Level × 100W`

Das ist eine Näherung! Die tatsächliche Leistung hängt von vielen Faktoren ab:
- Topfgröße und -material
- Induktionseffizienz
- Boost-Modus aktiv

Für präzise Messungen empfehlen wir einen externen Stromzähler (Shelly, etc.) am Kochfeld-Stromkreis.

---

## Tipps zur Konfiguration

### Stromverbrauch-Schwellenwerte ermitteln

1. Öffne **Entwicklerwerkzeuge → Zustände** in Home Assistant
2. Suche deinen Kochfeld-Power-Sensor
3. Beobachte die Werte beim Kochen:
   - Eine Platte auf Stufe 3: ca. 500-800W
   - Eine Platte auf Stufe 6: ca. 1200-1500W
   - Eine Platte auf Boost: ca. 2000-3000W
   - Zwei Platten gleichzeitig: addiere die Werte

### Hysterese richtig einstellen

- **Zu niedrig** (z.B. 50W): Häufiges Umschalten
- **Zu hoch** (z.B. 500W): Träge Reaktion
- **Empfehlung**: 100-200W für die meisten Kochfelder

### Nachlauf anpassen

- **Kurzes Kochen** (Aufwärmen): 5 Min Nachlauf reicht
- **Normales Kochen**: 10-15 Min Nachlauf
- **Intensives Braten**: 15-20 Min Nachlauf empfohlen

---

## Weitere Beispiele

Für komplexere Automationen siehe [docs/AUTOMATION_EXAMPLES.md](../docs/AUTOMATION_EXAMPLES.md)
