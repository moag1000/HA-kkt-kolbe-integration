# Security Policy

## Unterstützte Versionen

| Version | Unterstützt        |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

## Sicherheitslücke melden

**Bitte keine Sicherheitsprobleme in öffentlichen Issues melden!**

### Kontakt
- Email: security@moag1000.de
- Oder: Private Message an [@moag1000](https://github.com/moag1000)

### Was wir benötigen
1. Beschreibung der Schwachstelle
2. Schritte zur Reproduktion
3. Potenzielle Auswirkungen
4. Vorgeschlagene Lösung (falls vorhanden)

### Reaktionszeit
- Bestätigung: 48 Stunden
- Erste Einschätzung: 7 Tage
- Fix (kritisch): So schnell wie möglich

## Sicherheitshinweise

### Kochfeld-Steuerung
Diese Integration kann Kochfelder steuern. **Besondere Vorsicht!**

- Nie unbeaufsichtigt automatisieren
- Kindersicherung aktiviert lassen
- Regelmäßig physisch überprüfen
- Bei Zweifeln: Gerät vom Netz trennen

### Netzwerk
- Integration nutzt lokales Tuya-Protokoll
- Keine Cloud-Verbindung für Steuerung erforderlich
- Credentials werden lokal in Home Assistant gespeichert

### Best Practices
- Home Assistant aktuell halten
- Starke Passwörter verwenden
- Netzwerk absichern
- Regelmäßige Updates installieren

## Responsible Disclosure

Wir unterstützen Responsible Disclosure. Nach Behebung einer Schwachstelle:
- Veröffentlichung in CHANGELOG
- Credit an den Entdecker (falls gewünscht)
- Keine rechtlichen Schritte bei gutgläubiger Meldung

---

Vielen Dank für deinen Beitrag zur Sicherheit!
