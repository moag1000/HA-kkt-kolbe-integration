# 🔥 Induktionskochfeld Sicherheitshinweise

## 🤝 Manuelle Bestätigung erforderlich

### 📱 Wie funktioniert Remote-Steuerung?

**Gleiche Sicherheit wie in der Tuya App:**

1. **Befehl senden** (Home Assistant/Tuya App)
   ```
   "Zone 1 auf Stufe 5 setzen"
   ```

2. **Kochfeld reagiert**
   - 🔊 **Piep-Ton** ertönt
   - 💡 **Display zeigt Warnung**
   - ⏰ **30 Sekunden Timeout** startet

3. **Physische Bestätigung nötig**
   - 👤 **Person muss vor Ort sein**
   - 🔘 **Bestätigungstaste drücken** (meist mittlere Taste)
   - ✅ **Erst dann wird Befehl ausgeführt**

4. **Ohne Bestätigung**
   - ❌ **Befehl wird abgebrochen**
   - 🔕 **Kochfeld bleibt unverändert**

### 🛡️ Warum diese Sicherheit?

**Tuya API Sicherheitsfeature:**
- 🚫 **Verhindert versehentliche Aktivierung**
- 👨‍👩‍👧‍👦 **Schutz vor unbeaufsichtigter Nutzung**
- 🔥 **Brandschutz** durch Anwesenheitspflicht
- 📱 **Standard in allen Tuya Kochfeld-Apps**

### ❗ Das ist KEIN Bug!

**Häufige Missverständnisse:**
- ❌ "Die Integration funktioniert nicht"
- ❌ "Local Tuya ist defekt"
- ❌ "Home Assistant kann das Kochfeld nicht steuern"

**✅ Korrekte Erklärung:**
- ✅ **Tuya API Sicherheitsfeature**
- ✅ **Gleiche Bestätigung wie in Smart Life App**
- ✅ **Gewollte Sicherheitsmaßnahme**

### 🎯 Praktische Nutzung

**Sinnvolle Automation:**
```yaml
# ✅ GUTES Beispiel: Warnung vor dem Kochen
automation:
  - alias: "Kochfeld bereit machen"
    trigger:
      - platform: time
        at: "18:00:00"
    action:
      - service: notify.mobile_app
        data:
          message: "Kochfeld bereit zum Einschalten (Bestätigung am Gerät nötig)"
```

**❌ Problematische Automation:**
```yaml
# ❌ SCHLECHT: Automatisches Einschalten ohne Person
automation:
  - alias: "Auto-Kochen" # GEHT NICHT!
    trigger:
      - platform: state
        entity_id: person.michael
        to: "home"
    action:
      - service: number.set_value # Braucht Bestätigung!
        target:
          entity_id: number.cooktop_zone1_power
        data:
          value: 5
```

### 🔧 Debugging-Tipps

**Falls "nichts passiert":**

1. **Prüfen Sie das Kochfeld-Display**
   - Zeigt es eine Warnung?
   - Blinkt eine LED?
   - Ertönt ein Piep-Ton?

2. **Bestätigungstaste finden**
   - Meist mittlere Touch-Taste
   - Oder spezielle "Confirm" Taste
   - Im Handbuch nachschlagen

3. **Timing beachten**
   - Ca. 30 Sekunden Zeit für Bestätigung
   - Nach Timeout: Befehl wiederholen

4. **Home Assistant Logs prüfen**
   ```yaml
   logger:
     logs:
       custom_components.kkt_kolbe: debug
   ```

### 📞 Support

**Bei Problemen NICHT melden:**
- "Kochfeld reagiert nicht auf Befehle"
- "Integration ist defekt"
- "Remote-Steuerung funktioniert nicht"

**Sondern verstehen:**
- Dies ist normales, sicheres Verhalten
- Bestätigung am Gerät ist erforderlich
- API-Feature, nicht Integration-Bug

---

**🎯 Fazit: Die manuelle Bestätigung ist ein wichtiges Sicherheitsfeature, das verhindert, dass Kochfelder unbeaufsichtigt ferngesteuert werden können.**