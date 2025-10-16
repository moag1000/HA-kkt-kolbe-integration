# Security Guidelines

## 🔴 KRITISCHER HINWEIS: KI-GENERIERTER CODE

**DIESER CODE WURDE VOLLSTÄNDIG VON CLAUDE AI ERSTELLT UND NICHT GETESTET!**

Bei Kochfeldern können Programmierfehler zu:
- Überhitzung
- Ungewolltem Einschalten
- Gefährlichen Situationen
- Brand- oder Verbrennungsgefahr

**NUTZUNG AUF EIGENE GEFAHR!**

## ⚠️ IMPORTANT: Protecting Your Credentials

### NEVER commit or share:
- **Local Key** - Your Tuya device encryption key
- **Device ID** - Your specific device identifier
- **IP Addresses** - Your local network IPs
- **GPS Coordinates** - Location data
- **Personal Information** - Names, addresses, etc.

### Before Pushing to GitHub:

1. **Check ALL files** for sensitive data
2. **Use example files** with dummy values
3. **Add sensitive files to .gitignore**
4. **Never hardcode credentials** in the code

### Safe Storage Options:

1. **Home Assistant Secrets**:
   ```yaml
   # secrets.yaml
   kkt_kolbe_key: "your_actual_key_here"
   ```

2. **Environment Variables**:
   ```bash
   export TUYA_LOCAL_KEY="your_key"
   ```

3. **Configuration via UI**:
   - The integration asks for credentials during setup
   - Stored encrypted in Home Assistant

### If You Accidentally Commit Credentials:

1. **Immediately** change/regenerate the exposed keys
2. Remove the commit from history using `git rebase` or `BFG Repo-Cleaner`
3. Force push the cleaned repository
4. Consider the credentials compromised and unusable

### Example vs Real Configuration:

✅ **GOOD** (config_example.yaml):
```yaml
device_id: "bf735dfe2ad64fba7cXXXX"
local_key: "YOUR_LOCAL_KEY_HERE"
ip: "192.168.1.xxx"
```

❌ **BAD** (never commit):
```yaml
device_id: "bf735dfe2ad64fba7cpyhn"
local_key: "wGz8(Dz#a:*U{cBR"
ip: "79.195.80.216"
```

## Reporting Security Issues

If you find a security vulnerability, please:
1. **DO NOT** open a public issue
2. Contact the maintainer directly: @moag1000
3. Allow time for a fix before disclosure