# 🚀 RELEASE CHECKLIST - NIEMALS VERGESSEN!

## ⚠️ KRITISCHE SCHRITTE VOR JEDEM RELEASE

### 1. 📝 Versionsnummern aktualisieren
- [ ] `custom_components/kkt_kolbe/manifest.json` - "version" Feld
- [ ] `README.md` - releases-shield Badge URL (v1.X.X)
- [ ] `info.md` - releases-shield Badge URL (v1.X.X)
- [ ] `CHANGELOG.md` - neuen Eintrag hinzufügen (optional)

### 2. 🔍 Validierung
- [ ] Git Status prüfen - alle Änderungen committed?
- [ ] Alle Tests bestanden?
- [ ] Dokumentation aktuell?

### 3. 🏷️ Git Tagging & Release
- [ ] `git tag -a vX.X.X -m "Release vX.X.X: Description"`
- [ ] `git push origin main`
- [ ] `git push origin vX.X.X`
- [ ] `gh release create vX.X.X --title "vX.X.X: Title" --notes "Release notes"`

### 4. ✅ Verifikation
- [ ] GitHub Release sichtbar?
- [ ] Download funktioniert?
- [ ] Badge aktualisiert?

## 🔄 Nach Release
- [ ] Zurück zum Feature Branch (falls vorhanden)
- [ ] Main Fixes in Feature Branch mergen
- [ ] Weiterentwicklung fortsetzen

## ⚡ AUTOMATISIERUNG SCRIPT

```bash
#!/bin/bash
# release.sh - Automatisiertes Release Script

VERSION=$1
if [ -z "$VERSION" ]; then
  echo "Usage: ./release.sh v1.5.15"
  exit 1
fi

# 1. Update version in files
sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION#v}\"/" custom_components/kkt_kolbe/manifest.json
sed -i "s/version-v[0-9.]*/version-$VERSION/" README.md
sed -i "s/version-v[0-9.]*/version-$VERSION/" info.md

# 2. Commit, tag, and push
git add .
git commit -m "chore: Bump version to ${VERSION#v}"
git tag -a $VERSION -m "Release $VERSION"
git push origin main
git push origin $VERSION

# 3. Create GitHub release
gh release create $VERSION --title "$VERSION: Release" --generate-notes

echo "✅ Release $VERSION completed!"
```

## 🚨 ERINNERUNG: IMMER DIESE CHECKLISTE BEFOLGEN!