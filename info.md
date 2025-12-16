# KKT Kolbe Integration

<div align="center">
  <img src="https://raw.githubusercontent.com/moag1000/HA-kkt-kolbe-integration/main/icon.png" alt="KKT Kolbe Logo" width="128" height="128">
</div>

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
[![License][license-shield]][license-url]

## Home Assistant Integration für KKT Kolbe Geräte

Diese Integration bringt **KKT Kolbe Dunstabzugshauben** und **Induktionskochfelder** in Home Assistant.

### Unterstützte Geräte

#### Dunstabzugshauben
- **HERMES & STYLE** - 5-Stufen Lüfter, RGB Beleuchtung, Timer
- **HERMES** - 5-Stufen Lüfter, RGB Beleuchtung, Filterverwaltung
- **ECCO HCM** - 9-Stufen Lüfter, Multi-Light Control, Wasch-Modus
- **SOLO HCM** - Lüfter, Beleuchtung, Wasch-Modus

#### Induktionskochfeld
- **IND7705HC** - 5 Kochzonen, Timer pro Zone, Kindersicherung

### Installation

1. **HACS** → **Integrations** → **Custom repositories**
2. Repository: `https://github.com/moag1000/HA-kkt-kolbe-integration`
3. Kategorie: `Integration`
4. **Installieren** → **Home Assistant neustarten**
5. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → **KKT Kolbe**

### Konfiguration

- **Automatische Erkennung**: Geräte werden im Netzwerk gefunden
- **Manuelle Konfiguration**: IP-Adresse, Device ID, Local Key
- **API-Only**: Cloud-Setup mit Tuya API Credentials

### Hinweis

Diese Integration wurde mit Claude (Anthropic) entwickelt. Der Code ist Open Source und getestet, aber **Verwendung erfolgt auf eigene Verantwortung** - besonders bei der Kochfeld-Steuerung.

### Links

- [Dokumentation](https://github.com/moag1000/HA-kkt-kolbe-integration#readme)
- [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- [Releases](https://github.com/moag1000/HA-kkt-kolbe-integration/releases)

---

**Version**: 2.3.0 | **Lizenz**: MIT | **Autor**: [@moag1000](https://github.com/moag1000)

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge
[license-url]: https://opensource.org/licenses/MIT
[releases-shield]: https://img.shields.io/github/v/release/moag1000/HA-kkt-kolbe-integration?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
