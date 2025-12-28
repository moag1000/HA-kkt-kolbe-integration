# Apple Home / HomeKit Integration

Diese Anleitung beschreibt die Integration von KKT Kolbe Dunstabzugshauben mit Apple Home (HomeKit) und Siri.

## Unterstützte Funktionen

### Direkt in HomeKit verfügbar

| Entity | HomeKit-Typ | Siri-Befehle |
|--------|-------------|--------------|
| **Fan** (Lüfter) | Ventilator | "Hey Siri, schalte den Lüfter ein" |
| **Light** (Licht) | Glühbirne | "Hey Siri, schalte das Licht ein" |
| **Timer** | - | Nicht direkt verfügbar |
| **RGB Mode** | - | Via Szenen (siehe unten) |

### Fan-Steuerung

Die Fan-Entity wird in HomeKit als Ventilator erkannt:
- **Ein/Aus**: "Hey Siri, schalte den Dunstabzug ein/aus"
- **Geschwindigkeit**: "Hey Siri, stelle den Dunstabzug auf 50%"

Die Geschwindigkeitsstufen werden automatisch gemappt:
| HomeKit % | HERMES/STYLE | SOLO/ECCO HCM |
|-----------|--------------|---------------|
| 0% | off | 0 |
| 25% | low | 2-3 |
| 50% | middle | 4-5 |
| 75% | high | 6-7 |
| 100% | strong | 8-9 |

### Light-Steuerung

Die Light-Entity wird in HomeKit als Glühbirne erkannt:
- **Ein/Aus**: "Hey Siri, schalte das Küchenlicht ein"
- **Helligkeit**: Falls unterstützt (bei manchen Modellen)

## RGB-Modi via Szenen

HomeKit unterstützt keine Light-Effects nativ. Als Workaround können **Szenen** verwendet werden, die dann in der Apple Home App und via Siri steuerbar sind.

### Szenen einrichten

Erstelle eine Datei `scenes.yaml` (oder füge zu bestehender hinzu):

```yaml
# KKT Kolbe Dunstabzug RGB-Modi Szenen
# Diese Szenen ermöglichen die Steuerung der RGB-Beleuchtung über Apple Home/Siri

- id: dunstabzug_rgb_aus
  name: "Dunstabzug RGB Aus"
  icon: mdi:lightbulb-off
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Aus"

- id: dunstabzug_rgb_weiss
  name: "Dunstabzug Weiß"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Weiß"

- id: dunstabzug_rgb_rot
  name: "Dunstabzug Rot"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Rot"

- id: dunstabzug_rgb_gruen
  name: "Dunstabzug Grün"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Grün"

- id: dunstabzug_rgb_blau
  name: "Dunstabzug Blau"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Blau"

- id: dunstabzug_rgb_gelb
  name: "Dunstabzug Gelb"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Gelb"

- id: dunstabzug_rgb_lila
  name: "Dunstabzug Lila"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Lila"

- id: dunstabzug_rgb_orange
  name: "Dunstabzug Orange"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Orange"

- id: dunstabzug_rgb_cyan
  name: "Dunstabzug Cyan"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Cyan"

- id: dunstabzug_rgb_grasgruen
  name: "Dunstabzug Grasgrün"
  icon: mdi:lightbulb
  entities:
    select.kkt_kolbe_hermes_style_rgb_mode:
      state: "Grasgrün"
```

### Entity-Namen anpassen

**Wichtig:** Passe den Entity-Namen `select.kkt_kolbe_hermes_style_rgb_mode` an dein Gerät an!

Um deinen korrekten Entity-Namen zu finden:
1. **Entwicklerwerkzeuge** → **Zustände**
2. Suche nach `select.*rgb_mode`
3. Kopiere den vollständigen Entity-Namen

Beispiele für verschiedene Modelle:
- HERMES & STYLE: `select.kkt_kolbe_hermes_style_rgb_mode`
- HERMES: `select.kkt_kolbe_hermes_rgb_mode`
- ECCO HCM: `select.kkt_kolbe_ecco_hcm_rgb_mode`

### configuration.yaml einbinden

Falls du `scenes.yaml` als separate Datei nutzt, füge in `configuration.yaml` hinzu:

```yaml
scene: !include scenes.yaml
```

### Szenen in HomeKit freigeben

1. **HomeKit Controller Integration** in Home Assistant einrichten (falls noch nicht geschehen)
2. Die Szenen werden automatisch an HomeKit übertragen
3. In der **Apple Home App**: Szenen erscheinen unter "Szenen"

### Siri-Befehle für RGB-Modi

Nach der Einrichtung funktionieren folgende Befehle:
- "Hey Siri, aktiviere Dunstabzug Rot"
- "Hey Siri, aktiviere Dunstabzug Blau"
- "Hey Siri, aktiviere Dunstabzug RGB Aus"
- etc.

**Tipp:** Du kannst die Szenen-Namen in `scenes.yaml` beliebig anpassen, z.B.:
- "Küche Stimmungslicht Rot"
- "Abzug Blaulicht"

## ECCO/SOLO HCM Modelle

Für ECCO und SOLO HCM Hauben mit den Modi `white`, `colour`, `scene`, `music`:

```yaml
- id: dunstabzug_rgb_weiss
  name: "Dunstabzug Weiß"
  entities:
    select.kkt_kolbe_ecco_hcm_rgb_mode:
      state: "white"

- id: dunstabzug_rgb_farbe
  name: "Dunstabzug Farbwechsel"
  entities:
    select.kkt_kolbe_ecco_hcm_rgb_mode:
      state: "colour"

- id: dunstabzug_rgb_szene
  name: "Dunstabzug Szene"
  entities:
    select.kkt_kolbe_ecco_hcm_rgb_mode:
      state: "scene"

- id: dunstabzug_rgb_musik
  name: "Dunstabzug Musik"
  entities:
    select.kkt_kolbe_ecco_hcm_rgb_mode:
      state: "music"
```

## Light Effects (Alternative)

Ab Version 3.1.0 unterstützt die Light-Entity auch Effects direkt:

```yaml
# In der Entity sichtbar unter:
# light.kkt_kolbe_hermes_style_light → Attribute: effect_list
```

Diese Effects sind in Home Assistant nutzbar, werden aber **nicht** an HomeKit übertragen, da HomeKit keine Light-Effects unterstützt.

Für HomeKit-Steuerung der RGB-Modi empfehlen wir daher die Szenen-Lösung.

## Automatisierungen kombinieren

Du kannst Szenen mit Automatisierungen kombinieren:

```yaml
automation:
  - alias: "Dunstabzug beim Kochen"
    trigger:
      - platform: state
        entity_id: sensor.herd_power
        to: "on"
    action:
      - service: fan.turn_on
        target:
          entity_id: fan.kkt_kolbe_hermes_style_fan
        data:
          percentage: 50
      - service: scene.turn_on
        target:
          entity_id: scene.dunstabzug_rgb_weiss
```

## Tipps

1. **Szenen-Namen kurz halten**: Siri versteht kurze Namen besser
2. **Eindeutige Namen**: Vermeide ähnliche Namen bei mehreren Geräten
3. **Räume nutzen**: Weise Szenen Räumen zu für bessere Organisation
4. **Favoriten**: Markiere häufig genutzte Szenen als Favoriten in der Home App

## Fehlerbehebung

### Szenen erscheinen nicht in HomeKit

1. Prüfe ob HomeKit Bridge in Home Assistant aktiv ist
2. Starte Home Assistant neu nach Szenen-Änderungen
3. In der Home App: "Gerät hinzufügen" → Bridge erneut scannen

### Siri versteht Befehl nicht

1. Verwende eindeutige Szenen-Namen
2. Vermeide Umlaute im Szenen-Namen (z.B. "Gruen" statt "Grün")
3. Trainiere Siri: "Hey Siri, lerne Dunstabzug Rot"

### RGB-Modus ändert sich nicht

1. Prüfe den korrekten Entity-Namen in `scenes.yaml`
2. Teste die Szene direkt in Home Assistant (Entwicklerwerkzeuge → Dienste)
3. Prüfe ob das Gerät erreichbar ist (Device-Status in Integration)
