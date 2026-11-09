# KKT Kolbe Home Assistant Integration

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">

  **Home Assistant Integration für KKT Kolbe Küchengeräte**

  [![GitHub Release][releases-shield]][releases]
  [![HACS][hacsbadge]][hacs]
  [![License][license-shield]][license-url]
  [![Validate][validate-shield]][validate]
  [![Commit Activity][commits-shield]][commits]

  [![Buy Me A Coffee][coffee-shield]][coffee]

  *Dunstabzugshauben, Induktionskochfelder und Backöfen lokal steuern*
</div>

---

## Highlights v4.9

- **Home Assistant 2026.x** - modernisiert für HA 2026.9+ (Python 3.14), bereit für die Änderungen in HA 2026.12
- **Geräte-Ereignisse** - eigene Event-Entity pro Gerät: Verbindung verloren/wieder da, Wechsel lokal ↔ Cloud, Timer abgelaufen, Filterreinigung fällig, Fehler an Kochzone, plus Blueprint für Push-Benachrichtigungen
- **Actions mit Antwort** - `get_connection_status` und `get_firmware_info` liefern ihr Ergebnis per `response_variable` direkt an Skripte
- **Lokal + Cloud** - lokale Tuya-Steuerung, SmartLife-Cloud als Fallback inkl. MQTT-Push (~500 ms statt 30 s Polling)
- **Kein Developer Account nötig** - Setup via SmartLife/Tuya Smart App
- **6 Hauben-Familien + 1 Kochfeld + 1 Backofen** unterstützt

> **Hinweis:** Diese Integration wurde mit [Claude Code](https://claude.ai/code) entwickelt. Der Quellcode ist vollständig einsehbar. Verwendung auf eigene Verantwortung.

---

## Quick Start

```
1. SmartLife/Tuya Smart App installieren → KKT-Gerät hinzufügen
2. App: Ich → Einstellungen → Konto und Sicherheit → User Code kopieren
3. Home Assistant: Integration hinzufügen → "KKT Kolbe"
4. User Code eingeben → QR-Code mit App scannen → Fertig!
```

**[Ausführliche Anleitung →](docs/SMARTLIFE_SETUP.md)**

---

## Unterstützte Geräte

### Dunstabzugshauben

| Modell | Lüfter | Licht | RGB | Timer | Status |
|--------|--------|-------|-----|-------|--------|
| **HERMES & STYLE** | 5 Stufen | Helligkeit | 10 Modi | ✅ | ✅ Getestet |
| **HERMES** | 5 Stufen | Helligkeit | 10 Modi | ✅ | ✅ Verfügbar |
| **ECCO HCM** | 9 Stufen | Multi | 4 Modi | ✅ | ✅ Verfügbar |
| **SOLO HCM** | 9 Stufen | Multi | 4 Modi | ✅ | ✅ Verfügbar |
| **EASY / PLOOM** | 10 Stufen | ✅ | 10 Modi | ✅ | ✅ Verifiziert (Issue #5, #8) |
| **FLAT** | 5 Stufen | ✅ | - | ✅ | ✅ Verfügbar |

EASY-Modelle: EASY9005SM (90cm), EASY909SHCM (90cm), EASY609SHCM (60cm) - HERMES-basiert mit 10 Lüfterstufen. PLOOM6005 (G/M/S) nutzt dieselben DPs.

### Induktionskochfeld

| Modell | Zonen | Features | Status |
|--------|-------|----------|--------|
| **IND7705HC** | 5 | Power 0-25, Timer, Temp, Boost, Flex | ✅ Getestet |

### Backofen

| Modell | Features | Status |
|--------|----------|--------|
| **EB8313HC** | Programm (f1-f10, p1-p8), Temp 35-250°C, Timer, Tür-Sensor | ⚡ DPs bekannt, Integration ungetestet |

EB8313HC: Product Key `be8ooigdvjvy1q4a`, Protocol 3.4, DPs 101-120. DPs ermittelt von @Lucky-ESA (Issue #6) aus echtem Gerät. Integration implementiert aber noch nicht End-to-End getestet — Tester willkommen!

#### Weitere Backöfen (Tester gesucht)

| Modell | WiFi | Status |
|--------|------|--------|
| **EB8317HC** | Tuya/SmartLife | Vermutlich identisch mit EB8313HC - Tester gesucht |
| **EB8313ED** | Tuya/SmartLife, Kerntemperaturfühler | DPs unbekannt - Tester gesucht |

Falls du einen dieser Backöfen besitzt, hilf uns die korrekten DPs zu ermitteln:
[Issue erstellen](https://github.com/moag1000/HA-kkt-kolbe-integration/issues/new?template=new_device.md)

### Weitere Geräte gesucht

Hast du ein KKT Kolbe Gerät mit WiFi das hier nicht aufgeführt ist?
[Issue erstellen](https://github.com/moag1000/HA-kkt-kolbe-integration/issues/new?template=new_device.md)

---

## Installation

### Via HACS (Empfohlen)

1. HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/moag1000/HA-kkt-kolbe-integration`
3. Kategorie: Integration → Installieren → Neustarten

### Manuell

1. Neuestes [Release](https://github.com/moag1000/HA-kkt-kolbe-integration/releases) herunterladen
2. Ordner `custom_components/kkt_kolbe/` nach `config/custom_components/kkt_kolbe/` kopieren
3. Home Assistant neu starten

---

## Setup-Methoden

| Methode | Developer Account | Schwierigkeit | Empfohlen |
|---------|-------------------|---------------|-----------|
| **SmartLife QR-Code** | Nein | Einfach | ✅ |
| IoT Platform API | Ja | Mittel | - |
| Manual (tinytuya) | Nein | Schwer | - |

**[SmartLife Setup →](docs/SMARTLIFE_SETUP.md)** | **[tinytuya Guide →](known_configs/tinytuya_cloud_api_guide.md)** | **[Developer Guide →](docs/DEVELOPER_GUIDE.md)**

---

## Voraussetzungen

| Komponente | Version |
|------------|---------|
| Home Assistant | ≥ 2026.9.0 |
| Python | ≥ 3.14 (bringt Home Assistant 2026.x mit) |

---

## Automationen, Sprachsteuerung & KI

- **Geräte-Ereignisse:** Jedes Gerät hat eine Entity „Geräte-Ereignisse“ (`event.*`). In Automationen als Auslöser „Entität → Ereignis“ wählen, z. B. `timer_finished` für eine Benachrichtigung, wenn der Haubentimer abläuft. Fertig zum Import: Blueprint [Geräte-Ereignisse melden](blueprints/README.md).
- **Neu verbinden per Knopf:** Geräte mit lokaler Verbindung haben einen Button „Neu verbinden“ auf der Geräteseite, statt die Action `kkt_kolbe.reconnect_device` aufzurufen.
- **Actions mit Antwort:** `kkt_kolbe.get_connection_status` und `kkt_kolbe.get_firmware_info` geben ihr Ergebnis zurück:
  ```yaml
  - action: kkt_kolbe.get_connection_status
    response_variable: status
  - action: notify.notify
    data:
      message: "{{ status.statuses }}"
  ```
- **Assist / KI-Agents:** Haube, Licht und Lüfter lassen sich per Assist oder einem LLM-Agent steuern („Stell die Dunstabzugshaube auf Stufe 3“), wenn die Entities unter *Einstellungen → Sprachassistenten → Entitäten freigeben* freigegeben sind.

> ⚠️ **Sicherheit Kochfeld:** Gib Kochfeld-Entities (Zonen, Leistung, Timer, Hauptschalter) **nicht** für Sprachassistenten oder KI-Agents frei. Ein missverstandener Befehl darf keine Kochzone einschalten. Mehr dazu in [docs/COOKTOP_SAFETY.md](docs/COOKTOP_SAFETY.md).

---

## Dokumentation

| Thema | Link |
|-------|------|
| SmartLife Setup | [docs/SMARTLIFE_SETUP.md](docs/SMARTLIFE_SETUP.md) |
| Troubleshooting | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Blueprints | [blueprints/README.md](blueprints/README.md) |
| HomeKit Integration | [docs/HOMEKIT.md](docs/HOMEKIT.md) |
| Automation Examples | [docs/AUTOMATION_EXAMPLES.md](docs/AUTOMATION_EXAMPLES.md) |
| Kochfeld-Sicherheit | [docs/COOKTOP_SAFETY.md](docs/COOKTOP_SAFETY.md) |
| Developer Guide | [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |

---

## Bekannte Limitationen

- Lokale Steuerung braucht das Gerät im selben Netz; ohne lokale IP läuft alles über die SmartLife-Cloud
- RGB-, Helligkeits- und Szenen-DPs der Hauben gehen nur lokal (die Tuya-Cloud bietet sie nicht an)
- Modell-spezifische Konfigurationen, Firmware-abhängige Data Points

---

## Entwicklung & Quellen

### Verwendete Bibliotheken

| Bibliothek | Zweck | Lizenz |
|------------|-------|--------|
| [tinytuya](https://github.com/jasonacox/tinytuya) | Tuya Local Protocol | MIT |
| [tuya-device-sharing-sdk](https://github.com/tuya/tuya-device-sharing-sdk) | SmartLife QR-Code Auth | MIT |
| [pycryptodome](https://github.com/Legrandin/pycryptodome) | Tuya Encryption | BSD |

### Referenzen & Inspiration

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Home Assistant Core Integrations](https://github.com/home-assistant/core/tree/dev/homeassistant/components)
- [Tuya Official Integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/tuya)
- [LocalTuya](https://github.com/rospogrigio/localtuya) - Tuya Protocol Patterns
- [TuyaLocal](https://github.com/make-all/tuya-local) - Device Configurations

### KI-Entwicklung

Diese Integration wurde vollständig mit **[Anthropic Claude](https://anthropic.com)** entwickelt:
- Architektur-Design und Code-Generierung
- Test-Erstellung und Dokumentation
- Code Reviews und Optimierungen

Der gesamte Quellcode ist Open Source und einsehbar.

---

## Contributing

- **Bug Reports**: [Issue erstellen](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- **Feature Requests**: [Discussion starten](https://github.com/moag1000/HA-kkt-kolbe-integration/discussions)
- **Pull Requests**: Willkommen!
- **Hardware Tests**: Besonders wertvoll!

---

## Support

| Kanal | Link |
|-------|------|
| GitHub Issues | [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues) |
| Discussions | [Community](https://github.com/moag1000/HA-kkt-kolbe-integration/discussions) |

---

## Lizenz

MIT License - siehe [LICENSE](./LICENSE)

---

<div align="center">

**Made with ❤️ and 🤖 by [@moag1000](https://github.com/moag1000) & [Claude Code](https://claude.ai/code)**

</div>

[releases-shield]: https://img.shields.io/github/v/release/moag1000/HA-kkt-kolbe-integration?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
[validate-shield]: https://img.shields.io/github/actions/workflow/status/moag1000/HA-kkt-kolbe-integration/validate.yml?style=for-the-badge&label=Validate
[validate]: https://github.com/moag1000/HA-kkt-kolbe-integration/actions/workflows/validate.yml
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/moag1000/HA-kkt-kolbe-integration.svg?style=for-the-badge
[license-url]: https://github.com/moag1000/HA-kkt-kolbe-integration/blob/main/LICENSE
[commits-shield]: https://img.shields.io/github/commit-activity/m/moag1000/HA-kkt-kolbe-integration?style=for-the-badge
[commits]: https://github.com/moag1000/HA-kkt-kolbe-integration/commits/main
[coffee-shield]: https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black
[coffee]: https://buymeacoffee.com/moag1000
