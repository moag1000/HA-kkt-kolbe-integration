# Contributing to KKT Kolbe Integration

## 🤝 Beiträge erwünscht!

Da dieser Code vollständig von KI generiert wurde, sind Beiträge von echten Entwicklern sehr willkommen! Besonders:

- **Hardware-Tests** mit echten Geräten
- **Code-Reviews** und Fehlerkorrekturen
- **Sicherheits-Audits** besonders für Kochfeld-Steuerung
- **Unterstützung für weitere KKT Kolbe Modelle**

## 📋 Neue Geräte hinzufügen

### 1. Tuya IoT Platform Account erstellen

**WICHTIG**: Ein separater Account ist erforderlich! Ihr normaler Tuya/Smart Life App Account funktioniert NICHT.

1. Besuchen Sie https://iot.tuya.com/
2. Registrieren Sie sich für einen **neuen Developer Account**
3. Erstellen Sie ein Cloud-Projekt
4. **Devices** → **Link App Account** → Smart Life App verknüpfen
5. Alle Geräte sollten nun im Cloud-Projekt sichtbar sein

### 2. Device Model Daten abrufen

Nach der App-Verknüpfung:

1. Navigieren Sie zu **Cloud** → **API Explorer**
2. Wählen Sie **Device Management** → **Query Things Data Model**
3. Geben Sie Ihre **Device ID** ein (aus der App/Integration)
4. Führen Sie die Query aus

### 3. Feature Request erstellen

Erstellen Sie einen GitHub Issue mit:

```markdown
## Neues Gerät: [Modellname]

**Device Info:**
- Modell: KKT [Modellname]
- Device ID: bf....... (anonymisiert)
- Kategorie: [dcl/yyj/etc.]

**Query Things Data Model Output:**
```json
{
  "result": {
    "model": "{ ... vollständiger JSON Output ... }"
  }
}
```

**Gewünschte Funktionen:**
- [ ] Funktion 1
- [ ] Funktion 2
```

## 🔧 Code-Beiträge

### Sicherheit zuerst!
- **Kochfelder**: Besondere Vorsicht bei Leistungssteuerung
- **Validation**: Alle User-Inputs validieren
- **Error Handling**: Graceful degradation bei Gerätefehlern
- **Timeouts**: Verhindern von hängenden Verbindungen

### Code-Standards
- Folgen Sie Home Assistant [Development Standards](https://developers.home-assistant.io/)
- Verwenden Sie Type Hints
- Dokumentieren Sie komplexe Bitmasken-Operationen
- Schreiben Sie Tests für kritische Funktionen

### Testing

1. **Simulator verwenden**: Testen Sie zunächst ohne echte Hardware
2. **Schrittweise**: Beginnen Sie mit ungefährlichen Funktionen
3. **Monitoring**: Überwachen Sie Geräte während Tests
4. **Rollback**: Haben Sie einen Notfallplan

## 🐛 Bug Reports

### Für Hardware-Tester
Wenn Sie Probleme mit echter Hardware finden:

```markdown
## Bug Report

**Gerät:**
- Modell: [KKT Modell]
- Firmware: [falls bekannt]

**Problem:**
- Was passiert ist
- Was erwartet wurde

**Logs:**
```
Home Assistant Core Logs hier
```

**Sicherheit:**
- [ ] Keine Gefahr für Personen/Sachen
- [ ] Gerät verhält sich sicher
```

## 📞 Support

- **GitHub Issues**: Für Bugs und Feature Requests
- **Discussions**: Für allgemeine Fragen
- **Security Issues**: Kontaktieren Sie @moag1000 direkt

## ⚖️ Haftung

**WICHTIG**: Alle Beiträger bestätigen:
- Code wird auf eigene Gefahr bereitgestellt
- Keine Haftung für Schäden durch Code-Änderungen
- Besondere Vorsicht bei sicherheitskritischen Geräten

---

**Danke für Ihre Hilfe dabei, diese Integration sicherer und besser zu machen!** 🙏