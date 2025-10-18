# 🏷️ Kategorie-basierte Geräteerkennung

Die KKT Kolbe Integration nutzt jetzt offizielle Tuya-Kategorie-Spezifikationen für eine robuste, automatische Geräteerkennung.

## 🚀 Neue Features

### Automatische Erkennung via Tuya-Kategorien
- **YYJ-Kategorie** (Dunstabzugshauben) - 14 Funktionen
- **DCL-Kategorie** (Induktionskochfelder) - 11 Funktionen
- **XFJ-Kategorie** (Lüftungsanlagen) - 49 Funktionen
- Basiert auf offizieller Tuya API-Spezifikation
- Automatische Entity-Generierung ohne manuelle Konfiguration
- Fallback auf modell-basierte Erkennung für unbekannte Kategorien

### Unterstützte Funktionen

#### YYJ-Kategorie (Dunstabzugshauben)

| Funktion | Entity Type | Beschreibung |
|----------|-------------|--------------|
| `fan_speed_enum` | Select | Lüftergeschwindigkeit (off/low/middle/high/strong) |
| `switch_lamp` | Switch | Lichtstreifen-Steuerung |
| `light` | Switch | Hauptbeleuchtung |
| `countdown` | Number | Timer-Funktion (0-100 min) |
| `countdown_left` | Sensor | Verbleibende Timer-Zeit |
| `disinfection` | Switch | Desinfektions-Modus |
| `anion` | Switch | Negativ-Ionen Generator |
| `switch_wash` | Switch | Wasch-/Reinigungsmodus |
| `switch` | Switch | Hauptschalter |
| `warm` | Switch | Warmhalte-Funktion |
| `drying` | Switch | Trocknungs-Funktion |
| `fault` | Sensor | Fehlerstatus (e1, e2, e3) |
| `status` | Sensor | Gerätestatus (standby/working/sleeping) |
| `total_runtime` | Sensor | Gesamtbetriebszeit |

#### DCL-Kategorie (Induktionskochfelder)

| Funktion | Entity Type | Beschreibung |
|----------|-------------|--------------|
| `work_mode` | Select | Kochmodus (chips/drumsticks/shrimp/fish/ribs/meat) |
| `cook_temperature` | Number | Kochtemperatur (0-500°C) |
| `current_temperature` | Sensor | Aktuelle Temperatur |
| `cook_power` | Number | Kochleistung (0-5000W) |
| `switch` | Switch | Hauptschalter |
| `pause` | Switch | Pause/Weiter |
| `start` | Switch | Start-Funktion |
| `cook_time` | Number | Kochzeit (1-360 min) |
| `work_status` | Sensor | Arbeitsstatus (standby/appointment/cooking/done) |
| `remaining_time` | Sensor | Verbleibende Zeit |
| `appointment_time` | Number | Vorprogrammierte Zeit (1-360 min) |

#### XFJ-Kategorie (Lüftungsanlagen) - Top 15 Funktionen

| Funktion | Entity Type | Beschreibung |
|----------|-------------|--------------|
| `switch` | Switch | Hauptschalter |
| `mode` | Select | Betriebsmodus (auto/sleep/manual) |
| `fan_speed_enum` | Select | Lüftergeschwindigkeit (low/mid/high/sleep) |
| `supply_fan_speed` | Select | Zuluft-Geschwindigkeit |
| `exhaust_fan_speed` | Select | Abluft-Geschwindigkeit |
| `temp_indoor` | Sensor | Innentemperatur |
| `humidity_indoor` | Sensor | Innenfeuchtigkeit |
| `pm25` | Sensor | PM2.5 Feinstaub |
| `air_quality` | Sensor | Luftqualität (great/good/mild/medium/bad) |
| `primary_filter_life` | Sensor | Vorfilter-Lebensdauer (%) |
| `purification` | Switch | Luftreinigung |
| `anion` | Switch | Negativ-Ionen Generator |
| `sterilize` | Switch | Sterilisation |
| `child_lock` | Switch | Kindersicherung |
| `filter_reset` | Switch | Filter zurücksetzen |

*Insgesamt: 49 verfügbare Funktionen für komplette Lüftungssteuerung*

## 📋 Implementierung

### TuyaCategorySpecs
```python
from api.tuya_category_specs import TuyaCategorySpecs

specs = TuyaCategorySpecs()
supported = specs.get_supported_categories()  # ['yyj', 'dcl', 'xfj']
entities = specs.generate_device_config_from_category(
    device_id="12345",
    category="yyj"
)
```

### DynamicDeviceFactory (Enhanced)
```python
from api.dynamic_device_factory import DynamicDeviceFactory

factory = DynamicDeviceFactory()
device_config = await factory.analyze_device_properties({
    "result": {
        "device_id": "bf735dfe2ad64fba7c1234",
        "category": "yyj",  # Automatische Kategorie-Erkennung
        "name": "KKT Kolbe Hood"
    }
})
```

## 🔄 Erkennungsablauf

1. **Kategorie-Prüfung**: Ist `category` in API-Response vorhanden?
2. **Spezifikations-Check**: Haben wir eine Spezifikation für diese Kategorie?
3. **Entity-Generierung**: Automatische Erstellung aller verfügbaren Entities
4. **Fallback**: Bei Fehlschlag → Modell-basierte Erkennung

## 📁 Dateien

- `api/tuya_category_specs.py` - Kategorie-Spezifikationen und Mapping
- `api/dynamic_device_factory.py` - Erweiterte Factory mit Kategorie-Support
- `known_configs/yyj_category_info.json` - Offizielle YYJ-Spezifikation
- `CATEGORY_DETECTION.md` - Diese Dokumentation

## 🎯 Vorteile

✅ **Vollständige Abdeckung** - Alle verfügbaren Funktionen werden erkannt
✅ **Zukunftssicher** - Neue Tuya-Features automatisch unterstützt
✅ **Weniger Wartung** - Keine manuellen Gerätekonfigurationen
✅ **Bessere UX** - Mehr Entities und Funktionen verfügbar
✅ **Robustheit** - Offizielle Spezifikationen statt Reverse Engineering

## 🔮 Geplante Erweiterungen

- **Weitere Kategorien** (z.B. Klimaanlagen, Smart Lights)
- **Dynamisches Laden** von Kategorie-Spezifikationen via API
- **Live-Updates** der Spezifikationen ohne Integration-Update
- **KI-basierte Funktions-Gruppierung** für bessere UI-Organisation
- **Adaptive Entity-Icons** basierend auf Gerätekombinationen

## 📊 Aktuelle Abdeckung

| Kategorie | Gerätetyp | Funktionen | Status |
|-----------|-----------|------------|--------|
| **YYJ** | Dunstabzugshauben | 14 | ✅ Vollständig |
| **DCL** | Induktionskochfelder | 11 | ✅ Vollständig |
| **XFJ** | Lüftungsanlagen | 49 | ✅ Vollständig |
| **Gesamt** | **3 Kategorien** | **74 Funktionen** | **🎯 100%** |