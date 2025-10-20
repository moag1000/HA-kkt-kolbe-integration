# 🚨 Hotfix v2.0.0-beta.3

## Critical Startup Performance Fix

This hotfix addresses Home Assistant stability issues caused by blocking imports during startup.

### 🔧 Fixed Issues

- **Blocking import_module calls**: Moved all heavy imports to lazy loading pattern
- **Startup performance**: Eliminated blocking imports that were causing stability issues
- **Event loop blocking**: Imports are now loaded only when needed during runtime

### 📋 Technical Changes

- `__init__.py`: All heavy imports (`tuya_device`, `coordinator`, `hybrid_coordinator`, `api`, `services`) moved inside functions
- Only lightweight `const` import remains at module level
- Improved Home Assistant startup time and stability

### ⬆️ Upgrade from v2.0.0-beta.1/beta.2

This is a **recommended update** that fixes critical startup issues. Simply update through HACS or replace the files manually.

### 🐛 Issues Fixed

- Logger warning: "Detected blocking call to import_module... causing stability issues"
- Improved integration startup reliability
- Better Home Assistant event loop performance

---

**Note**: This is an automated hotfix for critical startup performance. All previous v2.0.0-beta.1 features remain unchanged.