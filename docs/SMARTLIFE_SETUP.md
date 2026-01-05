# SmartLife/Tuya Smart App Setup

Diese Anleitung erklaert das einfache Setup der KKT Kolbe Integration ueber die SmartLife oder Tuya Smart App.

**Kein Tuya Developer Account erforderlich!**

Der Local Key wird automatisch abgerufen - kein manuelles Kopieren aus der IoT Platform noetig.

---

## Voraussetzungen

Bevor du startest, stelle sicher dass:

- **SmartLife** ODER **Tuya Smart** App auf deinem Smartphone installiert ist
- Dein **KKT Kolbe Geraet** in der App eingerichtet und funktionsfaehig ist
- Du Zugang zu deinem **User Code** hast (siehe Anleitung unten)
- Home Assistant **2025.1.0** oder hoeher installiert ist

---

## Schritt-fuer-Schritt Anleitung

### Schritt 1: Integration in Home Assistant hinzufuegen

1. Oeffne Home Assistant
2. Gehe zu **Einstellungen** → **Geraete & Dienste**
3. Klicke auf **+ Integration hinzufuegen** (unten rechts)
4. Suche nach **KKT Kolbe**
5. Waehle die Integration aus der Liste

### Schritt 2: Setup-Methode waehlen

Im Willkommens-Dialog:

1. Waehle **SmartLife/Tuya Smart App** als Setup-Methode
2. Diese Option ist als **(empfohlen)** markiert
3. Klicke auf **Weiter**

### Schritt 3: User Code eingeben

1. Gib deinen **User Code** aus der App ein (z.B. `EU12345678`)
2. Waehle welche App du verwendest:
   - **SmartLife** - gruenes Icon
   - **Tuya Smart** - rotes Icon
3. Klicke auf **Weiter**

### Schritt 4: QR-Code scannen

Ein QR-Code wird auf dem Bildschirm angezeigt.

1. Oeffne die **SmartLife** oder **Tuya Smart** App auf deinem Smartphone
2. Gehe zu **Ich** (Profil-Tab, unten rechts)
3. Tippe auf das **QR-Code Symbol** (oben rechts)
4. Richte die Kamera auf den angezeigten QR-Code
5. **Bestaetige die Autorisierung** in der App, wenn du dazu aufgefordert wirst

Home Assistant wartet automatisch auf den Scan.

### Schritt 5: Geraet auswaehlen

Nach erfolgreicher Autorisierung:

1. Eine Liste deiner KKT Kolbe Geraete wird angezeigt
2. Waehle das Geraet, das du hinzufuegen moechtest
3. Die IP-Adresse wird automatisch ermittelt (falls moeglich)
4. Klicke auf **Hinzufuegen**

### Fertig!

Dein KKT Kolbe Geraet ist jetzt in Home Assistant verfuegbar und wird lokal gesteuert.

---

## Wo finde ich den User Code?

Der User Code ist eine eindeutige Kennung deines SmartLife/Tuya Accounts.

### In der SmartLife App:

1. Oeffne die **SmartLife** App
2. Tippe auf **Ich** (Profil-Tab, unten rechts)
3. Tippe auf das **Zahnrad-Symbol** (oben rechts) fuer Einstellungen
4. Waehle **Konto und Sicherheit** (oder "Account and Security")
5. Scrolle nach unten zu **User Code**
6. Der Code hat das Format: `XX12345678` (z.B. `EU12345678`)

### In der Tuya Smart App:

1. Oeffne die **Tuya Smart** App
2. Tippe auf **Ich** (Profil-Tab, unten rechts)
3. Tippe auf das **Zahnrad-Symbol** (oben rechts)
4. Waehle **Konto und Sicherheit**
5. Scrolle nach unten zu **User Code**

> **Hinweis:** Der Pfad kann je nach App-Version leicht variieren.
> Falls du "User Code" nicht findest, pruefe ob deine App aktuell ist.

---

## Wo finde ich den QR-Code Scanner?

Der QR-Code Scanner ist in beiden Apps an der gleichen Stelle:

1. Oeffne die App (SmartLife oder Tuya Smart)
2. Tippe auf **Ich** (Profil-Tab, unten rechts)
3. Tippe auf das **QR-Code Symbol** (oben rechts, neben den Einstellungen)

Der Scanner oeffnet sich und du kannst den QR-Code von Home Assistant scannen.

---

## Haeufige Fragen (FAQ)

### Mein Geraet erscheint nicht in der Liste

**Moegliche Ursachen:**

- Das Geraet ist nicht in der SmartLife/Tuya App eingerichtet
- Das Geraet ist offline oder nicht erreichbar
- Es handelt sich um ein nicht unterstuetztes Geraet

**Loesungen:**

1. Pruefe in der App, ob das Geraet angezeigt wird und funktioniert
2. Stelle sicher, dass das Geraet eingeschaltet und im WLAN ist
3. Versuche das Geraet in der App kurz ein- und auszuschalten
4. Pruefe ob es ein unterstuetztes KKT Kolbe Geraet ist (Dunstabzugshaube, Kochfeld)

### QR-Code Timeout / abgelaufen

Der QR-Code ist nur fuer ca. 2 Minuten gueltig.

**Loesung:**

1. Gehe in Home Assistant zurueck
2. Starte den Setup-Vorgang erneut
3. Scanne den neuen QR-Code zuegig

### Falsche App gewaehlt

Du hast im Setup "SmartLife" gewaehlt, aber du nutzt "Tuya Smart" (oder umgekehrt).

**Loesung:**

1. Brich das Setup ab
2. Starte erneut
3. Waehle die richtige App aus

### Token abgelaufen / Re-Authentifizierung erforderlich

Nach laengerer Zeit oder bei Problemen kann der Token ablaufen.

**Symptome:**

- Home Assistant zeigt "Re-Authentifizierung erforderlich"
- Geraet reagiert nicht mehr

**Loesung:**

1. Klicke in Home Assistant auf die Meldung
2. Folge dem Reauth-Flow
3. Gib deinen User Code erneut ein
4. Scanne den neuen QR-Code

### QR-Code wird nicht erkannt

**Moegliche Ursachen:**

- Bildschirm-Helligkeit zu niedrig
- Abstand zur Kamera nicht optimal
- Falsche App verwendet

**Loesungen:**

1. Erhoehe die Bildschirm-Helligkeit
2. Halte das Smartphone ca. 15-20 cm vom Bildschirm entfernt
3. Stelle sicher, dass du die im Setup gewaehlte App verwendest
4. Aktualisiere die App auf die neueste Version

### User Code nicht gefunden

**Moegliche Ursachen:**

- Alte App-Version
- Regionsspezifische Einschraenkungen

**Loesungen:**

1. Aktualisiere die App im App Store / Play Store
2. Versuche die andere App (SmartLife statt Tuya Smart oder umgekehrt)
3. Pruefe ob du in der richtigen Region eingeloggt bist

---

## Vergleich der Setup-Methoden

| Eigenschaft | SmartLife/Tuya App | IoT Platform | Manuell |
|-------------|-------------------|--------------|---------|
| Developer Account | Nicht noetig | Erforderlich | Nicht noetig |
| API-Subscription | Nicht noetig | Erforderlich (laeuft ab) | Nicht noetig |
| Setup-Zeit | ca. 1 Minute | ca. 15 Minuten | ca. 5 Minuten |
| Local Key | Automatisch | Automatisch | Manuell eingeben |
| Key-Updates | Automatisch | Automatisch | Manuell |
| Schwierigkeit | Einfach | Fortgeschritten | Mittel |
| Empfohlen fuer | Alle Nutzer | Entwickler mit bestehendem Account | Experten |

### Vorteile der SmartLife-Methode

- Kein Tuya IoT Developer Account erforderlich
- Keine API-Subscription die nach 1 Monat ablaeuft
- Local Key wird automatisch abgerufen
- Automatische Key-Updates bei Geraet-Re-Pairing
- Setup in unter 1 Minute

### Wann IoT Platform nutzen?

- Du hast bereits einen Tuya IoT Developer Account
- Du benoetigst erweiterte Debugging-Moeglichkeiten
- Du moechtest mehrere Tuya-Integrationen zentral verwalten

### Wann Manuelles Setup nutzen?

- Du kennst bereits IP, Device ID und Local Key
- Du moechtest komplett ohne Cloud-Verbindung arbeiten
- Du hast die Daten aus einer anderen Quelle (z.B. tinytuya)

---

## Technische Details

### Was passiert beim QR-Code Scan?

1. Home Assistant generiert einen einmaligen QR-Code mit deinem User Code
2. Die SmartLife/Tuya App scannt diesen Code
3. Du autorisierst Home Assistant in der App
4. Home Assistant erhaelt einen Access Token und Refresh Token
5. Mit diesen Tokens werden deine Geraete und deren Local Keys abgerufen
6. Der Local Key ermoeglicht die lokale Kommunikation mit dem Geraet

### Wie funktioniert die Token-Erneuerung?

- Tokens sind eine begrenzte Zeit gueltig (typisch 30-90 Tage)
- Home Assistant erneuert Tokens automatisch mit dem Refresh Token
- Falls der Refresh Token ablaeuft, wird eine Re-Authentifizierung noetig
- Du erhaeltst dann eine Benachrichtigung in Home Assistant

### Lokale vs. Cloud-Steuerung

Nach dem Setup:

- Die **Steuerung** erfolgt **lokal** ueber dein Heimnetzwerk
- **Keine Cloud-Verbindung** fuer den normalen Betrieb noetig
- Cloud wird nur fuer Token-Erneuerung und Local Key Updates verwendet
- Das Geraet funktioniert auch bei Internet-Ausfall (solange kein Key-Update noetig)

---

## Support

Bei Problemen:

1. Pruefe die [Troubleshooting-Dokumentation](../TROUBLESHOOTING.md)
2. Erstelle ein [GitHub Issue](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
3. Gib dabei an:
   - Home Assistant Version
   - Integration Version
   - Verwendete App (SmartLife oder Tuya Smart)
   - Fehlermeldung (falls vorhanden)
