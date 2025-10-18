# Aussagen zum Datenmodell des KKT Kolbe HERMES & STYLE Dunstabzugshauben

Basierend auf der Analyse des Datenmodells (model ID: e1k6i0zo) können folgende Aussagen getroffen werden:

## 1. Grundlegende Eigenschaften

- Das Gerät ist eine Dunstabzugshaube (Kategorie: hood) mit der Modell-ID "e1k6i0zo".
- Das Gerät verfügt über insgesamt 6 implementierte Datenpunkte (DPs).
- Alle Datenpunkte haben Lese- und Schreibzugriff (accessMode: "rw").

## 2. Verfügbare Funktionen

Das Datenmodell zeigt folgende Kernfunktionalitäten:

1. **Hauptschalter** (DP 1: "switch", Typ: bool)
   - Steuert die Ein/Aus-Funktion der Dunstabzugshaube
   - Aktueller Wert: true (eingeschaltet)

2. **Beleuchtung** (DP 4: "light", Typ: bool)
   - Steuert die Beleuchtung der Dunstabzugshaube
   - Aktueller Wert: false (ausgeschaltet)

3. **Filterreinigungserinnerung** (DP 6: "switch_lamp", Typ: bool)
   - Zeigt an, ob eine Filterreinigung erforderlich ist
   - Aktueller Wert: true (Reinigung erforderlich)

4. **Lüftergeschwindigkeit** (DP 10: "fan_speed_enum", Typ: enum)
   - Steuert die Geschwindigkeit des Lüfters
   - Verfügbare Optionen: "off", "low", "middle", "high", "strong"
   - Aktueller Wert: "off" (ausgeschaltet)

5. **Timer-Funktion** (DP 13: "countdown", Typ: value)
   - Stellt einen Countdown-Timer für die automatische Abschaltung ein
   - Wertebereich: 0-60 (Minuten)
   - Aktueller Wert: 0 (deaktiviert)

6. **RGB-Beleuchtung** (DP 101: "RGB", Typ: value)
   - Steuert den RGB-Beleuchtungsmodus
   - Wertebereich: 0-9 (verschiedene Farbmodi)
   - Aktueller Wert: 4 (ein bestimmter Farbmodus)

## 3. Integrationsdetails

- Die Home Assistant Integration unterstützt 6 Entitätstypen: Fan, Light, Switch, Sensor, Select und Number.
- Die Lüftersteuerung bietet 5 Geschwindigkeitsstufen.
- Die Beleuchtung unterstützt sowohl normale als auch RGB-Beleuchtung mit Helligkeitssteuerung.
- Die Timer-Funktion ermöglicht eine zeitgesteuerte Abschaltung zwischen 0-60 Minuten.

## 4. Vergleich mit tatsächlicher Implementierung

In der tatsächlichen Implementierung (device_types.py) werden mehr Funktionen definiert als im aktuellen Datenmodell aktiv genutzt werden, darunter:
- Verzögerte Abschaltung (DP 2)
- Automatikmodus (DP 3)
- Lichthelligkeit (DP 5)
- Temperatur-, Feuchtigkeits- und Luftqualitätssensoren (DP 7, 8, 9)
- Direkte Lüftergeschwindigkeitseinstellung (DP 11)
- Automatische Reinigung (DP 12)
- Filternutzungsstunden (DP 14)
- Filterreset (DP 15)
- Geräuschpegel (DP 16)
- Eco-Modus (DP 17)
- RGB-Helligkeit (DP 102)
- Farbtemperatur (DP 103)

Diese zusätzlichen Funktionen könnten in zukünftigen Firmware-Updates aktiviert werden oder sind für andere Varianten des gleichen Modells vorgesehen.