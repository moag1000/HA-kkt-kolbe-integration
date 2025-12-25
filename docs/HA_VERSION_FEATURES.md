# Home Assistant Version Features Reference

Diese Dokumentation enthält alle relevanten Home Assistant Features und wann sie eingeführt wurden.
Wird verwendet um die Mindestversion der Integration schrittweise anzuheben.

---

## Feature Timeline

### Home Assistant 2024.1
- **Valve Entity Type** - Neuer Entity-Typ für Ventile
- **Entity Registry Improvements** - Bessere Entity-Verwaltung

### Home Assistant 2024.2
- **Icon Translations** - Icons via `icons.json` statt Property-Methoden
- **More Voice Features** - Verbesserte Sprachsteuerung

### Home Assistant 2024.4
- **Labels/Categories** - Entities können kategorisiert werden
- **Organize Features** - Bessere Organisation von Entities

### Home Assistant 2024.5
- **Smaller Core** - Performance-Verbesserungen
- **Entity Descriptions** - Dataclass-basierte Entity-Definitionen

### Home Assistant 2024.6
- **Model IDs for Devices** - `model` Feld für Geräte
- **Visibility Options** - Entities können versteckt werden
- **Extra State Attributes Deprecation** - Start der Deprecation (entfernt in 2024.12)
- **`_unrecorded_attributes`** - Attribute von DB-Recording ausschließen

### Home Assistant 2024.8
- **Services renamed to Actions** - Terminologie-Änderung
- **Multi-press Events** - Separate Event-Typen für Mehrfach-Klicks
- **Beautiful Badges** - Neue Dashboard-Badges

### Home Assistant 2024.10
- **Button Entity Classification** - `IDENTIFY` Buttons müssen `DIAGNOSTIC` sein
- **Matter 1.3 Power/Energy Sensors** - Neue Sensor-Typen
- **Calories Unit** - Neue Einheit für Energie-Entities

### Home Assistant 2024.11
- **Config Flow Improvements** - Bessere Fehlerbehandlung
- **Coordinator Improvements** - Performance-Optimierungen

### Home Assistant 2024.12
- **Extra State Attributes Removed** - Deprecated Attributes entfernt
- **Scene Improvements** - Bessere Szenen-Unterstützung

### Home Assistant 2025.1 - 2025.5
- **`suggested_display_precision`** - Default-Präzision für Sensoren basierend auf Device Class
- **`has_entity_name = True`** - Pflicht für neue Integrationen
- **Translation Key Improvements** - Bessere Übersetzungsunterstützung

### Home Assistant 2025.6 - 2025.11
- **DataUpdateCoordinator Backoff** - `retry_after` Parameter für Rate-Limiting
- **OAuth2 Error Handling** - `ImplementationUnavailableError` Exception
- **Store Serialization Control** - `serialize_in_event_loop` Parameter

### Home Assistant 2025.12
- **Labs Framework** - Experimentelle Features für User aktivierbar
- **Service Translation Placeholders** - Dynamische Service-Beschreibungen
- **Purpose-Specific Triggers** - Spezifische Trigger für Automationen
- **Energy Dashboard Power Sensors** - Echtzeit-Power neben Energy

---

## Geplante Versionsanhebung

### Phase 1: v3.0.0 - Mindestversion 2024.6
**Neue Features:**
- `_unrecorded_attributes` für weniger DB-Last
- `model` ID für Geräte
- Konsistente `entity_category` Verwendung

**manifest.json:**
```json
{
  "homeassistant": "2024.6.0"
}
```

**Änderungen:**
- [ ] `_unrecorded_attributes` zu allen Entities hinzufügen
- [ ] `model` zu Device Info hinzufügen
- [ ] Alle Entities auf korrekte `entity_category` prüfen

---

### Phase 2: v3.1.0 - Mindestversion 2024.10
**Neue Features:**
- Button Entity Classification (DIAGNOSTIC für Identify-Buttons)
- Modernere Entity-Struktur

**manifest.json:**
```json
{
  "homeassistant": "2024.10.0"
}
```

**Änderungen:**
- [ ] Alle Button Entities mit korrekter Classification
- [ ] Entity Descriptions für bessere Code-Struktur

---

### Phase 3: v3.2.0 - Mindestversion 2025.1
**Neue Features:**
- `suggested_display_precision` für alle Sensoren
- `has_entity_name = True` für alle Entities
- `translation_key` für Entity-Namen aus Übersetzungen

**manifest.json:**
```json
{
  "homeassistant": "2025.1.0"
}
```

**Änderungen:**
- [ ] `suggested_display_precision` für Timer, Filter-Tage, etc.
- [ ] `has_entity_name = True` für alle Entity-Klassen
- [ ] `translation_key` statt hardcoded Namen
- [ ] strings.json mit Entity-Übersetzungen erweitern

---

### Phase 4: v3.3.0 - Mindestversion 2025.6
**Neue Features:**
- `retry_after` im DataUpdateCoordinator
- Besseres Error Handling

**manifest.json:**
```json
{
  "homeassistant": "2025.6.0"
}
```

**Änderungen:**
- [ ] Coordinator mit `retry_after` für API Rate-Limiting
- [ ] Verbessertes Error Handling mit spezifischen Exceptions

---

### Phase 5: v3.4.0 - Mindestversion 2025.12
**Neue Features:**
- Labs Framework für experimentelle Features
- Service Translation Placeholders

**manifest.json:**
```json
{
  "homeassistant": "2025.12.0"
}
```

**Änderungen:**
- [ ] Labs Integration für experimentelle Features (z.B. erweiterte RGB-Steuerung)
- [ ] Dynamische Service-Beschreibungen

---

## Syntax für manifest.json

```json
{
  "domain": "kkt_kolbe",
  "name": "KKT Kolbe Integration",
  "homeassistant": "2024.6.0",
  "version": "3.0.0",
  ...
}
```

Wenn die HA-Version niedriger ist als die Mindestversion:
- HACS zeigt Warnung an
- Installation/Update wird blockiert
- User muss erst HA aktualisieren

---

## Referenzen

- [Integration Manifest Docs](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Entity Documentation](https://developers.home-assistant.io/docs/core/entity/)
- [Sensor Entity Docs](https://developers.home-assistant.io/docs/core/entity/sensor/)
- [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)

---

*Letzte Aktualisierung: Dezember 2025*
