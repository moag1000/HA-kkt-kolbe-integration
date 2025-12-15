# Changelog

All notable changes to the KKT Kolbe Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.1] - 2025-12-15 🔧

### Hotfix Release - SOLO HCM Konfiguration korrigiert

**Focus**: Korrigierte Konfiguration basierend auf verifiziertem Things Data Model.

### Fixed
- **SOLO HCM Konfiguration komplett überarbeitet**
  - Model ID korrigiert: `edjszs` (nicht HERMES-basiert)
  - **SOLO HCM = ECCO HCM** (identische DP-Struktur!)
  - Jetzt mit korrekten DPs: 102 (fan_speed), 105 (countdown_1), etc.

### Changed
- **SOLO HCM Features aktualisiert** (basierend auf Community Things Data Model):
  - ✅ 9-Stufen Lüftersteuerung (0-9) via DP 102
  - ✅ RGB Beleuchtung (white/colour/scene/music) via DP 107/108
  - ✅ Duale Filterüberwachung (Kohle DP 103, Metall DP 109)
  - ✅ Timer (0-60 min) via DP 105
  - ✅ Multi-Light Control (Main, LED, RGB)

### Documentation
- `known_configs/SOLO_HCM_datenpunkte.md` komplett aktualisiert mit verifiziertem Things Data Model
- Vergleichstabelle: SOLO HCM vs ECCO HCM vs HERMES

### Thanks
- 🙏 Danke an **@selinamulle123** für das Things Data Model!

---

## [2.4.0] - 2025-12-12 🆕

### New Device Support

**Focus**: Initial support for KKT Kolbe SOLO HCM range hood.

### Added
- **KKT Kolbe SOLO HCM Hood**: Initial configuration (later corrected in v2.4.1)

### Notes
- ⚠️ v2.4.0 hatte falsche DP-Konfiguration (HERMES-basiert statt ECCO-basiert)
- Bitte auf v2.4.1 updaten!

---

## [2.2.4] - 2025-01-05 🔧

### Hotfix Release - Smart Home Industry Project Support

**Focus**: Authentication fix for Tuya Smart Home Industry projects.

### Fixed
- **Token Authentication for Smart Home Projects**: Added nonce (UUID) support for Industry project authentication
  - Token requests now include nonce in HMAC signature calculation
  - API requests use standard signature without nonce
  - Compatible with both IoT Core and Smart Home Industry project types
- **Removed unnecessary Content-Type header** from GET requests for better API compatibility

### Technical Details
- Signature format for token: `HMAC-SHA256(client_id + t + nonce + stringToSign, secret)`
- Signature format for API calls: `HMAC-SHA256(client_id + access_token + t + stringToSign, secret)`
- Dynamic nonce generation only for token acquisition
- Fixes Error 1004 "sign invalid" for Smart Home Industry accounts

---

## [2.2.3] - 2025-01-05 🔧

### Hotfix Release - Full v2.0 API Migration

**Focus**: Complete migration to v2.0 API endpoints for all operations.

### Added
- **v2.0 Things Data Model API**: Device properties via `/v2.0/cloud/thing/{id}/model`
  - Includes ALL device properties (including RGB on HERMES & STYLE)
  - Parses nested JSON model structure
  - Extracts properties from services
  - Triple fallback: v2.0 → v1.0 iot-03 → v1.0 legacy

### Fixed
- **Missing RGB Property**: Now detected via v2.0 Things Data Model (abilityId 101)
- **Complete Free Tier Support**: All three core endpoints now use v2.0 first
  - Device List: ✅ v2.2.1
  - Device Status: ✅ v2.2.2
  - Device Properties: ✅ v2.2.3

### Technical Details
- Parse JSON string in `result.model` field
- Extract properties from `services[].properties[]`
- Convert v2.0 format to v1.0-compatible structure
- Three-level fallback for maximum compatibility

---

## [2.2.2] - 2025-01-05 🔧

### Hotfix Release - Complete v2.0 API Support

**Focus**: Full v2.0 API compatibility for Free tier accounts.

### Fixed
- **Device Status v2.0 Support**: Added Shadow Properties API support (`/v2.0/cloud/thing/{id}/shadow/properties`)
  - Handles nested response structure (`result.properties[]`)
  - Automatic fallback to v1.0 for older accounts
  - Fixes status polling for Free tier users
- **Field Normalization**: Converts v2.0 camelCase to v1.0 snake_case
  - `localKey` → `local_key`
  - `productId` → `product_id`
  - `isOnline` → `online`

### Technical Details
- `get_device_status()`: v2.0 Shadow Properties with v1.0 fallback
- `_normalize_device_response()`: Automatic field name conversion
- Full compatibility with both Free and Paid Tuya accounts

---

## [2.2.1] - 2025-01-05 🔧

### Hotfix Release - Free Tier API Support

**Focus**: Critical fixes for Tuya Free tier accounts and sensor setup.

### Fixed
- **Tuya API v2.0 Support**: Added support for v2.0 API endpoints (`/v2.0/cloud/thing/device`)
  - Free tier accounts can now use the integration
  - Automatic fallback to v1.0 for older accounts
  - Fixes Error 1004 "sign invalid" for Free tier users
- **Sensor Setup Error**: Removed leftover DIAGNOSTIC_DPS reference causing NameError
- **Version References**: Updated all documentation to v2.2.0

### Technical Details
- `tuya_cloud_client.py`: v2.0 API with v1.0 fallback
- `sensor.py`: Cleaned up entity category handling
- Compatible with both Free and Paid Tuya accounts

---

## [2.2.0] - 2025-01-05 🏆

### Home Assistant Gold Tier Quality Release - 100% COMPLETE

**Focus**: Advanced features, comprehensive documentation, and FULL Gold Tier compliance.

### Added
- **Entity Disabled by Default**: 46 advanced/diagnostic entities disabled by default (Gold Tier)
- **Automatic IP Updates**: Discovery automatically updates device IP addresses when they change (Gold Tier)
- **Stale Device Cleanup**: Automatically removes devices not seen for 30+ days (Gold Tier)
- **Repair Flows**: Three automated repair flows for common issues (Gold Tier):
  - Tuya API authentication failed → Triggers reauth flow
  - Wrong Tuya region/endpoint → Allows region selection
  - Local key expired/invalid → Allows key update
- **Comprehensive Documentation**:
  - `AUTOMATION_EXAMPLES.md` - 15+ ready-to-use automation examples
  - `USE_CASES.md` - Detailed implementation guides for various scenarios
  - `GOLD_TIER_CHECKLIST.md` - Quality compliance documentation
- **Enhanced API Error Messages**: Detailed Tuya API error reporting with error codes and solutions

### Changed
- **Quality Scale**: Upgraded from Silver to Gold Tier (21/21 requirements met - 100%)
- **Discovery**: Enhanced zeroconf listener with automatic config entry updates
- **Device Management**: Periodic stale device check every 24 hours
- **API Client**: Improved error handling with specific error codes (1004, 1010, 1011)
- **Error Handling**: Automatic repair issue creation for authentication and configuration errors

### Fixed
- Enhanced Tuya API error logging with detailed troubleshooting information
- Discovery update service now properly updates IP addresses in config entries

### Documentation
- 15+ automation examples (hood, cooktop, combined, voice control)
- Comprehensive use case guides (home setups, user personas, cooking scenarios)
- Gold Tier compliance checklist with detailed status
- Enhanced API troubleshooting

---

## [2.1.0] - 2025-01-XX 🥈

### Home Assistant Silver Tier Quality Release

**Focus**: Reliability, error handling, and Home Assistant best practices compliance.

### Added
- **Options Flow**: Post-setup UI configuration (scan interval, local key update, debug logging)
- **Diagnostics Download**: Debug information export with sensitive data redaction
- **Entity Categories**: Diagnostic entities properly categorized
- **Advanced Entities**: Less-used entities disabled by default
- **Test Coverage**: 21 automated tests (config flow, setup, entities, diagnostics)

### Changed
- **Error Handling** (Silver Tier):
  - `ConfigEntryAuthFailed` for authentication → automatic reauth flow
  - `ConfigEntryNotReady` for temporary failures → automatic retry
  - `CancelledError` properly handled with cleanup
- **Connection Timeouts**: Optimized (30s→15s overall, 5s→3s socket)
- **Logging**: Reduced excessive logging for offline devices (DEBUG level)
- **Executor Jobs**: Using `hass.async_add_executor_job()` (HA best practice)

### Fixed
- `CancelledError` during protocol auto-detection
- Duplicate `async_get_options_flow()` registration
- Test fixtures (real ConfigEntry instead of Mock)
- Empty device_id in diagnostics
- Authentication error detection (decrypt/encrypt/hmac keywords)

### Documentation
- Comprehensive troubleshooting section (5 common problems with solutions)
- Debug information collection guide
- Support request template
- Silver Tier compliance status

---

## [2.0.0] - 2024-12-XX 🎉

### Major Release: Global API Management

Siehe v2.0.0-beta.1 für Details der API Integration.

---

## [2.0.0-beta.1] - 2024-10-20

### 🎯 Major Beta Release: TinyTuya API & Enhanced Stability

This release introduces significant architectural improvements and new features while maintaining backward compatibility for existing users.

### Added
- **TinyTuya Cloud API Integration**
  - Full API client implementation with authentication
  - Hybrid coordinator supporting local/cloud fallback
  - Shadow properties for real-time synchronization
  - Dynamic device factory from API metadata
  - API discovery for automatic device detection

- **Enhanced Reconnection System**
  - Automatic reconnection with exponential backoff
  - Device state tracking (ONLINE, OFFLINE, RECONNECTING, UNREACHABLE)
  - Health monitoring with periodic checks
  - Manual reconnection service
  - Connection status service

- **Improved Authentication**
  - Reauth flow for expired credentials
  - Local key update service for device resets
  - API credential management
  - Support for multiple auth methods

- **New Services**
  - `reconnect_device`: Manually trigger device reconnection
  - `update_local_key`: Update local key after device reset
  - `get_connection_status`: Query current connection state

### Changed
- Updated to modern asyncio APIs (`get_running_loop()`)
- Enhanced state caching mechanism for all entity types
- Improved error handling order (error → log)
- Refactored coordinator architecture for better modularity
- Updated all dependencies to latest versions
- Enhanced timeout handling with `async_timeout`

### Fixed
- Deprecated `config_entry` usage (HA 2025.12 compatibility)
- `asyncio.get_event_loop()` deprecation warnings
- Error handling order throughout codebase
- State caching for all entity types
- Falsy value handling (0, False) in bitfield utils
- Connection stability issues with retry logic

### Technical Improvements
- Full Home Assistant best practices compliance
- Comprehensive type hints throughout codebase
- Enhanced logging with proper error context
- Improved resource management and cleanup
- Better exception handling and recovery

## [1.7.10] - 2024-10-19

### Fixed
- **HOTFIX**: JSON syntax error in English translation file
- Missing commas in translation structure causing parsing failures

## [1.7.9] - 2024-10-19

### Added
- **State Caching System**
  - Intelligent value storage preventing "unknown" states
  - Timestamp tracking for last successful updates
  - Cached values persist during temporary disconnections

### Changed
- Enhanced config flow with full device ID display
- Improved UI with proper newline rendering
- Selective advanced entities (only for induction cooktops)

### Fixed
- All device configurations standardized
- RGB mode values corrected (0-9 range)
- Light switch entities consistent across all hood models

## [1.7.8] - 2024-10-18

### Fixed
- Complete fix for all unknown entity states
- Enhanced data point availability checking
- Improved zone-specific entity handling

## [1.7.7] - 2024-10-18

### Fixed
- **CRITICAL**: Falsy values (0, False) incorrectly treated as None
- Bitfield utilities now properly handle all valid values
- Power level 0 and temperature 0 now work correctly

## [1.7.6] - 2024-10-18

### Added
- Enhanced debug logging for troubleshooting unknown entities
- Detailed data point availability reporting

## [1.7.5] - 2024-10-17

### Fixed
- HERMES & STYLE fan entity configuration
- IND7705HC zone entity mappings
- Improved entity availability detection

## [1.7.4] - 2024-10-17

### Fixed
- HERMES & STYLE hood fan speed control
- Proper DP mapping for fan operations

## [1.7.2] - 2024-10-17

### Fixed
- **HOTFIX**: Temperature unit configuration
- Celsius as default unit for cooktop zones

## [1.7.1] - 2024-10-17

### Added
- Critical Home Assistant best practices implementation
- Enhanced error handling and logging

## [1.6.2] - 2024-10-16

### Fixed
- **HOTFIX**: ECCO HCM fan entity configuration
- Corrected fan speed mappings

## [1.6.1] - 2024-10-16

### Fixed
- **HOTFIX**: Fan entity fix for HERMES & STYLE hood
- Proper speed level handling

## [1.6.0] - 2024-10-16

### Added
- Zone-organized entities for better user experience
- Enhanced entity categorization
- Improved device organization

## [1.5.16] - 2024-10-15

### Fixed
- **HOTFIX**: Enhanced connection stability
- Improved timeout handling
- Better error recovery

## Earlier Versions

For changes prior to v1.5.16, please refer to the git commit history.

---

[2.0.0-beta.1]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v2.0.0-beta.1
[1.7.10]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.7.10
[1.7.9]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.7.9