# KKT Kolbe Integration - Troubleshooting Guide

## Quick Diagnostics

Check the **Device Connected** and **Cloud API Connected** sensors in Home Assistant to quickly see the connection status.

---

## ⚠️ Häufige Probleme & Lösungen

### 1. "Failed to connect" / "Device not responding"

**Mögliche Ursachen:**
- Gerät ist offline oder nicht im Netzwerk erreichbar
- Falsche IP-Adresse
- Firewall blockiert Port 6668
- Device ID oder Local Key falsch

**Lösungen:**

1. **Netzwerk prüfen:**
   ```bash
   ping 192.168.1.100  # Deine Gerät-IP
   ```

2. **Port-Erreichbarkeit testen:**
   ```bash
   telnet 192.168.1.100 6668
   ```

3. **Firewall-Regel hinzufügen** (falls nötig):
   - Erlaube ausgehende Verbindungen auf Port 6668
   - Für Docker/VM: Bridge-Netzwerk prüfen

4. **IP-Adresse validieren:**
   - Router-Admin-Interface → DHCP-Clients
   - Smart Life App → Geräteinfo
   - DHCP-Reservation empfohlen!

5. **Device ID/Local Key neu extrahieren:**
   - Verwende TinyTuya Wizard oder Tuya IoT Platform
   - Bei Fehlern: Gerät in Smart Life App neu einrichten

---

### 2. "Authentication failed" / "Invalid local key"

**Symptom:** Integration startet Reauth-Flow automatisch

**Ursache:** Local Key ist falsch oder wurde geändert

**Lösungen:**

1. **Neuen Local Key extrahieren:**
   - TinyTuya Wizard erneut ausführen
   - Oder Tuya IoT Platform nutzen

2. **Reauth-Flow nutzen:**
   - Benachrichtigung in Home Assistant klicken
   - Neuen Local Key eingeben
   - Integration wird automatisch neu verbunden

3. **Häufige Fehler:**
   - ❌ Local Key enthält Leerzeichen → Entfernen
   - ❌ Groß-/Kleinschreibung → Exakt kopieren
   - ❌ Unvollständiger Key → Muss 16+ Zeichen sein

**Key Format:**
- Local key muss genau 16 Zeichen sein
- Keine Leerzeichen oder Sonderzeichen
- Groß-/Kleinschreibung beachten

---

### 3. Entities zeigen "unavailable" / "unknown"

**Temporäre Unavailable (< 5 Minuten):**
- Normal beim Home Assistant Neustart
- Gerät neu hochgefahren
- → Keine Aktion nötig, wartet auf Reconnect

**Dauerhafte Unavailable (> 5 Minuten):**

**Lösungen:**

1. **Integration neu laden:**
   - Einstellungen → Geräte & Dienste
   - KKT Kolbe → ⋮ → Integration neu laden

2. **Coordinator Status prüfen:**
   - Entwicklerwerkzeuge → Zustände
   - Suche nach `sensor.*.last_update`
   - Wenn Timestamp alt: Connection Problem

3. **Debug Logging aktivieren:**
   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.kkt_kolbe: debug
   ```
   Home Assistant neustarten → Log prüfen

4. **Gerät in Tuya App prüfen:**
   - Ist es dort online?
   - Funktioniert manuelle Steuerung?
   - Falls nein: Gerät neu starten

---

### 4. "Device discovery failed" / Gerät wird nicht gefunden

**Bei Automatic Discovery:**

**Lösungen:**

1. **Zeroconf/mDNS prüfen:**
   - Einige Router blockieren mDNS
   - Multicast-Support aktivieren
   - Alternative: Manuelles Setup nutzen

2. **Gleiches Netzwerk:**
   - Home Assistant und Gerät im selben VLAN
   - Keine Netzwerk-Isolation (IoT-VLAN trennen)

3. **Gerät neu starten:**
   - Power-Cycle des Geräts
   - 30 Sekunden warten
   - Discovery erneut versuchen

**Workaround:** Nutze **Manual Local Setup** oder **API-Only Setup**

---

### 5. API-Only Setup schlägt fehl

**Error: "API authentication failed"**

**Lösungen:**

1. **Credentials prüfen:**
   - Access ID (Client ID) korrekt?
   - Access Secret korrekt kopiert?
   - Richtige Region gewählt? (EU/US/CN/IN)

2. **API Services aktiviert?**
   - [Tuya IoT Platform](https://iot.tuya.com)
   - Cloud Project → Service API
   - Alle erforderlichen APIs aktivieren

3. **App Account verknüpft?**
   - Smart Life App mit Cloud Project verbunden?
   - QR-Code gescannt?
   - Geräte sichtbar in Tuya IoT Platform?

**Error: "No devices found"**

**Lösungen:**

1. **App Account Link prüfen:**
   - Tuya IoT Platform → Cloud → Devices
   - Sind deine Geräte gelistet?
   - Falls nein: App Account erneut verknüpfen

2. **Geräte-Region:**
   - Stelle sicher, Projekt und Geräte in gleicher Region
   - EU-Geräte brauchen EU Data Center

---

### 6. Connection Timeouts

**Symptoms:**
- "Operation timed out" errors
- Intermittent connectivity

**Solutions:**

1. **Check Network Stability:**
   - Ensure stable WiFi signal at device location
   - Consider WiFi extender if signal is weak

2. **Check IP Address:**
   - Device IP may change (use DHCP reservation)
   - Reconfigure with new IP if changed

3. **Firewall/Router Issues:**
   - Ensure UDP ports 6666-6668 are not blocked
   - Local communication uses these ports

4. **Use Hybrid Mode:**
   - Configure API credentials for fallback
   - Cloud API can work when local fails

---

### 7. Fan Speed Not Changing

**Symptoms:**
- Setting fan speed has no effect
- Fan shows wrong speed

**Solutions:**

1. **Check Power State:**
   - Fan must be powered on first
   - Turn on via Power switch before setting speed

2. **Wait for Response:**
   - Device may take 1-2 seconds to respond
   - Check if physical fan speed changed

3. **Check Device Mode:**
   - Some hoods have auto mode that overrides manual speed
   - Disable auto mode if available

---

### 8. Light Not Responding

**Symptoms:**
- Light commands don't work
- Light state incorrect

**Solutions:**

1. **Check Physical Button:**
   - Try controlling light with physical button on device
   - If that doesn't work, device issue

2. **Check Power State:**
   - Some models require main power on for light control

3. **LED vs Main Light:**
   - Some hoods have multiple light types (LED, RGB, main)
   - Ensure you're controlling the correct one

---

### 9. SmartLife QR-Code Probleme

**Problem: "QR-Code wird nicht angezeigt"**

**Mögliche Ursachen:**
- Netzwerkprobleme beim Laden des QR-Codes
- Ungültiger oder abgelaufener User Code
- Smart Life App nicht aktualisiert

**Lösungen:**

1. **User Code validieren:**
   - Öffne Smart Life App
   - Navigiere zu: Me → Settings → Account and Security → User Code
   - Kopiere den Code exakt (keine Leerzeichen)
   - Stelle sicher, dass der Code noch gültig ist (max. 24 Stunden)

2. **Internetverbindung prüfen:**
   - Stelle sicher, dass Home Assistant Zugriff auf das Internet hat
   - Falls VPN/Proxy: Tuya Server-Verbindung prüfen
   - Try opening the QR code URL directly in browser

3. **App neu installieren:**
   - Smart Life App deinstallieren und erneut installieren
   - Bei Problemen: Tuya Smart App statt SmartLife versuchen

---

**Problem: "QR-Code Scan Timeout"**

**Symptom:** Scan nicht innerhalb von 2 Minuten abgeschlossen

**Ursachen:**
- Scan dauert zu lange
- QR-Code Session abgelaufen
- Home Assistant verliert Verbindung

**Lösungen:**

1. **Erneut versuchen:**
   - QR-Code erneut anzeigen
   - In Home Assistant auf "Scan QR-Code" klicken
   - QR-Code innerhalb von 2 Minuten scannen

2. **App-Berechtigungen prüfen:**
   - Kamera-Berechtigung für Smart Life App erteilt?
   - iOS/Android: Einstellungen → Smart Life → Kamera aktivieren
   - App neu starten

3. **QR-Code direkt einscannen:**
   - Falls Web-QR-Code nicht funktioniert: Manuell eingeben
   - User Code direkt in Integration eingeben (Alternative)

---

**Problem: "Keine KKT Geräte gefunden"**

**Symptom:** Nach erfolgreichem QR-Code Scan werden keine Geräte angezeigt

**Ursache:** Geräte sind nicht in Smart Life App registriert

**Lösungen:**

1. **Geräte in Smart Life App registrieren:**
   - Öffne Smart Life App
   - Tippe "+" → Füge neues Gerät hinzu
   - Folge den Schritten zur Geräte-Registrierung
   - Stelle sicher, dass das KKT-Gerät online ist

2. **Richtige Region auswählen:**
   - Smart Life App: Me → Settings → Region
   - Muss mit der Region des Geräts übereinstimmen
   - EU-Geräte: Europa-Region
   - Andere Regionen: Entsprechend auswählen

3. **Cloud Account synchronisieren:**
   - Tuya IoT Platform → Cloud → Devices
   - Sind deine Geräte dort sichtbar?
   - Falls nein: Account erneut verknüpfen

---

**Problem: "User Code nicht gefunden"**

**Symptom:** Integration zeigt "User Code is invalid" oder ähnliche Fehler

**Lösung - User Code richtig finden:**

1. **In Smart Life App:**
   ```
   Me → Settings → Account and Security → User Code
   ```
   - Der Code wird hier angezeigt
   - Kopiere ihn exakt (Groß-/Kleinschreibung beachten)
   - Keine Leerzeichen oder Sonderzeichen

2. **Unterschied zwischen SmartLife und Tuya Smart:**
   - **SmartLife:** Me → Settings → Account and Security
   - **Tuya Smart:** My → Settings → Account Security
   - Die User Codes sind unterschiedlich!
   - Verwende den Code aus der App, die du für die Integration nutzt

3. **Code prüfen:**
   - User Code muss alphanumerisch sein
   - Mindestens 8-10 Zeichen
   - Falls Code nicht sichtbar: App aktualisieren und erneut versuchen

---

### 10. Token-Erneuerung und Session-Probleme

**Problem: "Token abgelaufen"**

**Symptom:**
- Gerät wird plötzlich nicht mehr aktualisiert
- Keine neue Daten von Tuya Cloud API
- "Authentication token expired" in Logs

**Lösung:**

1. **Integration neu hinzufügen:**
   - Einstellungen → Geräte & Dienste
   - KKT Kolbe Integration entfernen
   - Home Assistant neu starten
   - Integration erneut hinzufügen
   - QR-Code neu scannen

2. **Alternative - Reauth-Flow nutzen:**
   - Falls Integration noch angezeigt wird
   - Home Assistant zeigt Benachrichtigung
   - Klicke auf "Re-authenticate"
   - Scannen Sie den QR-Code erneut

3. **Automatische Token-Erneuerung:**
   - Token werden normalerweise automatisch erneuert
   - Falls fehlerhaft: Debugs aktivieren
   - Log prüfen auf "Token refresh failed"

---

**Problem: "Local Key hat sich geändert"**

**Symptom:**
- Integration funktioniert, aber "Authentication failed" in Logs
- Gerät antwortet nicht mehr lokal

**Ursachen:**
- Gerät wurde in Smart Life App zurückgesetzt
- Firmware Update durchgeführt
- Local Key wurde regeneriert

**Lösung:**

1. **SmartLife Setup erneut durchführen:**
   - Gerät in Smart Life App zurücksetzen
   - Schalte das Gerät aus und wieder ein
   - Warte 10 Sekunden
   - Füge das Gerät erneut in Smart Life App hinzu

2. **Local Key neu extrahieren:**
   - Nutze TinyTuya Wizard: `python -m tinytuya wizard`
   - Oder Tuya IoT Platform
   - Neuen Local Key kopieren
   - In Integration aktualisieren (Reauth-Flow)

3. **Hybrid Mode verwenden:**
   - Konfiguriere auch API-Credentials
   - Cloud API funktioniert auch wenn Local Key falsch
   - Fallback bei Local Connection Problemen

---

### 11. SmartLife vs. Tuya Smart App-Unterschiede

**Problem: "Welche App soll ich verwenden?"**

**Unterschiede zwischen den Apps:**

| Aspekt | SmartLife | Tuya Smart |
|--------|-----------|-----------|
| **Region** | Europa, Amerika (preferred) | Asien, Global |
| **Geräte-Zugriff** | Gleich | Gleich (anderer Server) |
| **User Code** | Unterschiedlich | Unterschiedlich |
| **API-Zugang** | EU Data Center | Variabel nach Region |
| **KKT Kolbe Support** | Empfohlen | Funktioniert auch |

**Empfehlung:**

1. **Beste Wahl für KKT Kolbe:**
   - Verwende die App, in der du das Gerät ursprünglich registriert hast
   - Normalerweise: **SmartLife** für europäische Geräte
   - Falls unsicher: Smart Life App bevorzugen

2. **Falls dein Gerät in Tuya Smart registriert ist:**
   - Verwende Tuya Smart App konsistent
   - User Code aus Tuya Smart App nehmen
   - API-Region auf "Asia" oder entsprechend einstellen

3. **Falls Probleme auftreten:**
   - Geräte in **beide Apps** hinzufügen
   - QR-Code von der App scannen, die besser funktioniert
   - Falls eine App nicht funktioniert: Zur anderen wechseln

**Tipps zum Wechsel zwischen Apps:**

```
1. Gerät physisch zurücksetzen (Power-Zyklus)
2. Neu in bevorzugter App registrieren
3. QR-Code von neuer App scannen
4. Integration mit neuem User Code aktualisieren
```

---

## 🔍 Debug Logging

### Enable Debug Logging

**Option 1: Via UI (Recommended)**
1. Go to Settings > Integrations > KKT Kolbe
2. Click "Configure"
3. Enable "Debug Logging"
4. Reload the integration

**Option 2: Via configuration.yaml**
```yaml
logger:
  default: info
  logs:
    custom_components.kkt_kolbe: debug
```

### View Logs

```bash
# In Home Assistant logs, filter for kkt_kolbe:
Logger: custom_components.kkt_kolbe
```

### Important Log Messages

| Message | Meaning |
|---------|---------|
| `Device connected successfully` | Local connection working |
| `Authentication failed` | Wrong local key |
| `Timeout connecting` | Network issue |
| `DP X not in current update` | Data point temporarily unavailable (normal) |
| `Circuit breaker opened` | Multiple failures, temporary disconnect |
| `Reconnecting...` | Automatic reconnection attempt |

---

## 📊 Data Points Reference

### Range Hood DPs

| DP | Function | Type |
|----|----------|------|
| 1 | Power (on/off) | Boolean |
| 4 | Light (on/off) | Boolean |
| 10 | Fan Speed | Enum/Numeric |
| 13 | Timer (minutes) | Integer (0-60) |
| 6 | Filter Status | Boolean |
| 101 | RGB Mode | Integer (0-9) |

### Induction Cooktop DPs

| DP | Function | Type |
|----|----------|------|
| 101 | Zone States (bitfield) | Integer |
| 102 | Zone Power Levels (bitfield) | Integer |
| 103 | Zone Timers (bitfield) | Integer |
| 106 | Global Settings | Integer |

---

## 🔍 Debug-Informationen sammeln

Für Support-Anfragen bitte folgende Infos bereitstellen:

### 1. System-Info
```yaml
Home Assistant Version: 2025.x.x  # Mindestens 2025.12.0
KKT Kolbe Integration Version: 4.0.0
Installation Method: HACS / Manual
Python Version: 3.12+
```

### 2. Gerät-Info
```yaml
Device Model: DH9509NP / IND7705HC / etc.
Firmware Version: (aus Smart Life App)
Setup Method: Discovery / Manual / API-Only
IP Address: 192.168.1.100
```

### 3. Debug Log
```bash
# configuration.yaml aktivieren, dann:
cat home-assistant.log | grep "kkt_kolbe"
```

### 4. Diagnostics Download
1. Einstellungen → Geräte & Dienste
2. KKT Kolbe Device → ⋮ → Download diagnostics
3. Datei an GitHub Issue anhängen

---

## 📞 Getting Help

### Before Asking for Help

1. Enable debug logging
2. Reproduce the issue
3. Collect relevant log entries
4. Note your device model and firmware version

### Where to Get Help

- **GitHub Issues:** [Report Bug](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- **Discussions:** GitHub Discussions for questions

### Issue Template

```markdown
## Problem Description
[Beschreibe das Problem]

## Steps to Reproduce
1. ...
2. ...

## Expected Behavior
[Was sollte passieren]

## Actual Behavior
[Was passiert tatsächlich]

## Environment
- HA Version:
- Integration Version:
- Device Model:

## Logs
[Debug logs hier einfügen]
```

---

## ⚠️ Known Limitations

1. **Local Discovery:** May not work across VLANs/subnets
2. **Some Features:** Not all device features may be exposed
3. **Firmware Updates:** May temporarily break integration (rare)
4. **Multiple Hoods:** Each device needs separate setup
5. **mDNS:** Some routers block multicast traffic

---

## 🔄 Reset and Reinstall

If all else fails:

1. Remove the integration from Settings > Integrations
2. Restart Home Assistant
3. Re-add the integration
4. Re-pair device in Smart Life app if needed (last resort)

---

## Related Documentation

- **[README](./README.md)** - Main documentation
- **[Developer Guide](./docs/DEVELOPER_GUIDE.md)** - Technical documentation
- **[Cooktop Safety](./docs/COOKTOP_SAFETY.md)** - Safety guidelines for cooktop
- **[Automation Examples](./docs/AUTOMATION_EXAMPLES.md)** - Example automations
