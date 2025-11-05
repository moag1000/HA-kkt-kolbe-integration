# KKT Kolbe Home Assistant Integration v2.1.0 🥈

## Home Assistant Silver Tier Quality Release

This release focuses on **reliability**, **error handling**, and **Home Assistant best practices compliance** to achieve Silver Tier quality status.

---

## ✨ What's New

### 🎯 Silver Tier Features

- **Options Flow**: Configure scan interval, update local key, and enable debug logging after setup
- **Diagnostics Download**: Export debug information for troubleshooting (with sensitive data redaction)
- **Entity Categories**: Diagnostic entities properly categorized and disabled by default
- **Test Coverage**: 21 automated tests for config flow, setup, entities, and diagnostics

### 🛡️ Enhanced Error Handling

- **Authentication Errors**: Automatic reauth flow when credentials expire
- **Connection Failures**: Smart retry logic for temporary network issues
- **Timeout Optimization**: Faster connection detection (15s instead of 30s)
- **CancelledError Handling**: Proper cleanup when operations are cancelled

### 📚 Improved Documentation

- Comprehensive troubleshooting guide with 5 common problems and solutions
- Debug information collection instructions
- Support request template
- Silver Tier compliance documentation

---

## 🔧 Technical Improvements

### Error Handling (Silver Tier Compliance)
- `ConfigEntryAuthFailed` triggers automatic reauth flow
- `ConfigEntryNotReady` enables automatic retry for temporary failures
- Proper `CancelledError` handling with resource cleanup
- Authentication error detection (decrypt/encrypt/hmac keywords)

### Performance Optimizations
- Connection timeout: 30s → 15s
- Socket timeout: 5s → 3s
- Reduced excessive logging for offline devices (DEBUG level)
- Using `hass.async_add_executor_job()` for blocking operations

### Entity Management
- Diagnostic entities disabled by default (Gold Tier best practice)
- Advanced entities only enabled for relevant device types
- Proper entity categorization throughout

---

## 🐛 Bug Fixes

- Fixed `CancelledError` during protocol auto-detection
- Removed duplicate `async_get_options_flow()` registration
- Fixed test fixtures (real ConfigEntry instead of Mock)
- Fixed empty device_id handling in diagnostics
- Improved authentication error detection

---

## 📋 Breaking Changes

**None** - This release is fully backward compatible with v2.0.0.

---

## 🔄 Upgrade Instructions

### Via HACS (Recommended)
1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Search for "KKT Kolbe"
4. Click "Update"
5. Restart Home Assistant

### Manual Installation
1. Download the latest release
2. Copy `custom_components/kkt_kolbe` to your Home Assistant installation
3. Restart Home Assistant

---

## 📖 Documentation

- **README**: [English](README.md) | [Deutsch](README.de.md)
- **Full Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Troubleshooting**: See README.md
- **Issue Tracker**: https://github.com/moag1000/HA-kkt-kolbe-integration/issues

---

## 🙏 Acknowledgments

Thank you to all users who reported issues and provided feedback to help improve this integration!

---

## 📊 Quality Status

| Tier | Status | Requirements Met |
|------|--------|------------------|
| Bronze | ✅ Pass | 100% |
| Silver | ✅ **Pass** | 100% |
| Gold | ⏳ In Progress | 67% (14/21) |

---

## 🔜 What's Next?

Future releases will focus on achieving Gold Tier status:
- Discovery IP update mechanism
- Stale device cleanup
- Additional entity defaults
- More automation examples

---

**Full Changelog**: https://github.com/moag1000/HA-kkt-kolbe-integration/compare/v2.0.0...v2.1.0
