# 🚀 KKT Kolbe Integration v2.0.0-beta.1

## 🎯 Major Release: TinyTuya API & Enhanced Stability

This beta release introduces significant architectural improvements, API support, and enhanced device management capabilities.

## ✨ New Features

### 🌐 TinyTuya Cloud API Support
- **Hybrid Communication**: Seamless fallback between local and cloud API
- **API Discovery**: Automatic device detection via Tuya Cloud
- **Shadow Properties**: Real-time device state synchronization
- **Dynamic Configuration**: Auto-configure devices from API metadata

### 🔄 Advanced Reconnection System
- **Automatic Reconnection**: Smart reconnection with exponential backoff
- **Device State Tracking**: ONLINE, OFFLINE, RECONNECTING, UNREACHABLE states
- **Health Monitoring**: Periodic health checks every 5 minutes
- **Manual Recovery**: Service to manually trigger reconnection

### 🔑 Enhanced Authentication
- **Reauth Flow**: Automatic reauthentication when credentials expire
- **Local Key Update**: Service to update local keys after device reset
- **API Credential Management**: Secure storage and refresh of API tokens
- **Multiple Auth Methods**: Support for local-only, API-only, or hybrid modes

### 🛠️ New Services
- `reconnect_device`: Manually reconnect offline devices
- `update_local_key`: Update local key when device is reset
- `get_connection_status`: Query current connection state

## 🔧 Technical Improvements

### Home Assistant Compliance
- ✅ Fixed deprecated `config_entry` usage (HA 2025.12 compatible)
- ✅ Updated to `asyncio.get_running_loop()` (Python 3.10+)
- ✅ Proper error handling order (error → log)
- ✅ Enhanced timeout handling with `async_timeout`
- ✅ Full DataUpdateCoordinator pattern compliance

### Stability Enhancements
- **State Caching**: Prevents "unknown" states during temporary disconnections
- **Improved Error Recovery**: Graceful degradation with fallback strategies
- **Connection Pooling**: Efficient resource management
- **Concurrent Operations**: Parallel tool execution support

### Code Quality
- **Type Hints**: Comprehensive type annotations
- **Error Messages**: Detailed, actionable error reporting
- **Logging**: Structured logging with appropriate levels
- **Documentation**: Inline documentation and service descriptions

## 📦 Installation

### Via HACS (Custom Repository)
1. Add custom repository: `https://github.com/moag1000/HA-kkt-kolbe-integration`
2. Install "KKT Kolbe Integration (Beta)"
3. Restart Home Assistant
4. Add integration via UI

### Manual Installation
```bash
# Download beta release
cd custom_components
git clone -b v2.0.0-beta.1 https://github.com/moag1000/HA-kkt-kolbe-integration kkt_kolbe
```

## 🔄 Migration from v1.x

### Breaking Changes
- Minimum Home Assistant version: 2024.1.0
- Python 3.10+ required
- New dependency: `aiohttp>=3.8.0`

### Migration Steps
1. **Backup** your current configuration
2. **Update** to v2.0.0-beta.1
3. **Restart** Home Assistant
4. **Reconfigure** if using API features
5. **Test** all automations

## 🧪 Beta Testing Focus

Please test and report on:
- **Reconnection**: Does automatic reconnection work reliably?
- **API Integration**: Cloud API fallback functionality
- **Local Key Updates**: Service for updating keys after reset
- **Performance**: Resource usage and response times
- **Stability**: Long-term operation without crashes

## 🐛 Known Issues

- API rate limiting not yet implemented
- Some advanced cooktop features may need refinement
- Translation strings need review for completeness

## 📝 Changelog

### Added
- TinyTuya Cloud API client implementation
- Hybrid coordinator with local/cloud fallback
- Automatic reconnection system with backoff
- Reauth flow for expired credentials
- Services for device management
- Dynamic device factory from API data
- Shadow properties integration
- Comprehensive error handling

### Changed
- Updated to DataUpdateCoordinator pattern
- Migrated to modern asyncio APIs
- Enhanced state caching mechanism
- Improved error logging order
- Refactored coordinator architecture

### Fixed
- Deprecated config_entry usage
- asyncio.get_event_loop() deprecation
- Error handling order (error → log)
- State caching for all entity types
- Falsy value handling (0, False)
- Connection stability issues

### Security
- Secure credential storage
- API token refresh handling
- No plaintext secrets in logs

## 🤝 Contributing

Beta feedback is crucial! Please report:
- GitHub Issues: [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- Feature Requests: Tag with `enhancement`
- Beta Feedback: Tag with `beta-testing`

## ⚠️ Disclaimer

This is a BETA release. While extensively tested, it may contain bugs.
- **Use at your own risk**
- **Not recommended for production**
- **Backup before installing**
- **Report all issues**

## 👏 Acknowledgments

Special thanks to:
- Beta testers providing valuable feedback
- Home Assistant community for best practices
- TinyTuya project for protocol implementation

---

**Version**: 2.0.0-beta.1
**Release Date**: October 2024
**Compatibility**: Home Assistant 2024.1.0+
**License**: MIT