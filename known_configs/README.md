# Known Device Configurations

Dieses Verzeichnis enthält Referenzdaten für unterstützte KKT Kolbe Geräte.

## Struktur

| Datei | Beschreibung |
|-------|-------------|
| `*_datenpunkte.md` | Dokumentation aller Datenpunkte (DPs) pro Gerät |
| `*_things_data_model.json` | Tuya API Things Data Model Export |
| `*_properties.json` | Geräte-Properties aus der API |
| `*_property_codes.txt` | Liste der Property-Codes |
| `*_api_curl_request_example*.txt` | API Request Beispiele (anonymisiert) |

## Geräte

### Verifiziert
- **HERMES & STYLE** - Dunstabzugshaube, 5 Stufen, RGB, Helligkeit
- **HERMES** - Dunstabzugshaube, 5 Stufen, RGB, Helligkeit
- **FLAT** - Dunstabzugshaube, 5 Stufen, ohne RGB
- **ECCO HCM** - Dunstabzugshaube, 9 Stufen, RGBW, Dualfilter
- **SOLO HCM** - Dunstabzugshaube, 9 Stufen, RGBW, Dualfilter
- **IND7705HC** - Induktionskochfeld, 5 Zonen, Bitfield-DPs

### Verifiziert durch Community (Issue #5)
- **EASY** - EASY9005SM, EASY909SHCM, EASY609SHCM (HERMES-basiert, Model-ID: e1my0pj8, 10 Stufen, RGB DP 102)

### DPs ermittelt durch Community (Issue #6) — Integration ungetestet
- **EB8313HC** - Backofen, WiFi/Tuya, Protocol 3.4, DPs 101-120 (Product Key: be8ooigdvjvy1q4a). DPs aus echtem Gerät (@Lucky-ESA), Integration implementiert aber End-to-End ungetestet

### In Vorbereitung (DPs unbekannt)
- **EB8317HC** - Backofen, WiFi/Tuya - Tester gesucht (vermutlich identisch mit EB8313HC)
- **EB8313ED** - Backofen, WiFi/Tuya, Kerntemperaturfühler - Tester gesucht

## Für Entwickler

Diese Dateien dienen als Referenz beim Hinzufügen neuer Geräte.
Siehe [Developer Guide](../docs/DEVELOPER_GUIDE.md) für Details.
