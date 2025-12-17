# Contributing to KKT Kolbe Integration

Vielen Dank für dein Interesse an diesem Projekt!

## Schnellstart

### Bug melden
1. [Issue erstellen](https://github.com/moag1000/HA-kkt-kolbe-integration/issues/new?template=bug_report.md)
2. Home Assistant Version angeben
3. Logs beifügen

### Neues Gerät anfragen
1. [Device Request erstellen](https://github.com/moag1000/HA-kkt-kolbe-integration/issues/new?template=new_device.md)
2. Tuya IoT Platform Daten bereitstellen

### Code beitragen
1. Fork erstellen
2. Feature Branch: `git checkout -b feature/mein-feature`
3. Änderungen committen
4. Pull Request erstellen

## Entwicklung

### Setup
```bash
# Repository klonen
git clone https://github.com/moag1000/HA-kkt-kolbe-integration.git
cd HA-kkt-kolbe-integration

# Dependencies installieren
pip install -r requirements_test.txt

# Tests ausführen
pytest tests/ -v
```

### Code Standards
- Python 3.12+
- Type Hints verwenden
- Home Assistant [Development Standards](https://developers.home-assistant.io/) folgen
- Tests für neue Features

### Wichtig bei Kochfeld-Code
- Sicherheit hat oberste Priorität
- Alle Eingaben validieren
- Keine unbeabsichtigte Aktivierung ermöglichen
- Ausgiebig testen

## Hilfe benötigt

Besonders gesucht:
- Hardware-Tests mit echten Geräten
- Neue KKT Kolbe Modelle (VIVA, SANDRA, etc.)
- Übersetzungen
- Dokumentation

## Kontakt

- **Issues**: Bugs & Features
- **Discussions**: Fragen & Ideen
- **Security**: security@moag1000.de (für Sicherheitsprobleme)

---

Detaillierte Informationen: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
