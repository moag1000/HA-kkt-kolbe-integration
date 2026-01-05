# Release Checklist

## Vor dem Release

### 1. Versionsnummern aktualisieren
- [ ] `custom_components/kkt_kolbe/manifest.json` - "version" Feld
- [ ] `README.md` - releases-shield Badge
- [ ] `info.md` - releases-shield Badge
- [ ] `CHANGELOG.md` - neuen Eintrag hinzufügen

### 2. Validierung
- [ ] Git Status prüfen - alle Änderungen committed?
- [ ] Tests bestanden?
- [ ] Dokumentation aktuell?

### 3. Git Tagging & Release
```bash
git tag -a vX.X.X -m "Release vX.X.X: Description"
git push origin main
git push origin vX.X.X
gh release create vX.X.X --title "vX.X.X: Title" --notes "Release notes"
```

### 4. Verifikation
- [ ] GitHub Release sichtbar?
- [ ] Download funktioniert?
- [ ] Badge aktualisiert?

## SmartLife Validation (v4.0.0+)

### QR-Code Flow
- [ ] User Code Eingabe funktioniert
- [ ] QR-Code wird generiert und angezeigt
- [ ] QR-Code Scan mit SmartLife App erfolgreich
- [ ] QR-Code Scan mit Tuya Smart App erfolgreich
- [ ] Timeout nach 2 Minuten ohne Scan
- [ ] Retry nach Timeout funktioniert

### Device Selection
- [ ] Nur KKT Kolbe Geräte werden angezeigt
- [ ] Bereits konfigurierte Geräte werden gefiltert
- [ ] Multi-Select funktioniert
- [ ] Unbekannte Modelle können Typ auswählen

### Entry Creation
- [ ] Device Entry wird erstellt
- [ ] Token-Info wird gespeichert
- [ ] Local Key wird korrekt übernommen
- [ ] IP-Adresse wird übernommen (falls vorhanden)

### Error Handling
- [ ] Ungültiger User Code zeigt Fehlermeldung
- [ ] Netzwerkfehler werden behandelt
- [ ] "Keine KKT Geräte" zeigt Fallback zu Manual

## Nach dem Release
- [ ] Weiterentwicklung fortsetzen

## Automatisierung

```bash
#!/bin/bash
# release.sh - Automatisiertes Release Script

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: ./release.sh v2.3.0"
  exit 1
fi

# Update version in files
sed -i '' "s/\"version\": \".*\"/\"version\": \"${VERSION#v}\"/" custom_components/kkt_kolbe/manifest.json
sed -i '' "s/version-v[0-9.]*/version-$VERSION/" README.md
sed -i '' "s/version-v[0-9.]*/version-$VERSION/" info.md

# Commit, tag, and push
git add .
git commit -m "chore: Bump version to ${VERSION#v}"
git tag -a $VERSION -m "Release $VERSION"
git push origin main
git push origin $VERSION

# Create GitHub release
gh release create $VERSION --title "$VERSION" --generate-notes

echo "Release $VERSION completed"
```
