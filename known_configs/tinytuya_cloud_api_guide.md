# tinytuya Cloud API Capabilities

> **💡 Hinweis: Es gibt jetzt eine einfachere Methode!**
>
> Seit Version 4.0.0 können Sie die **SmartLife QR-Code Methode** verwenden,
> die **keinen Developer Account** erfordert. Siehe [SmartLife Setup Guide](../docs/SMARTLIFE_SETUP.md).
>
> Diese Anleitung beschreibt die manuelle Methode über die Tuya IoT Platform,
> die für fortgeschrittene Nutzer oder Entwickler interessant sein kann.

Based on the official tinytuya documentation (https://github.com/jasonacox/tinytuya), the library **does** support cloud API access to Tuya devices in addition to its local control capabilities. Here's a summary of tinytuya's cloud API features:

## Cloud API Support

tinytuya supports the Tuya cloud API through the `Cloud` class that provides access to Tuya IoT cloud platform APIs. This functionality requires:

1. A Tuya IoT developer account
2. A cloud project with API keys
3. Authentication credentials (access ID, access secret, and region)

## Core Cloud API Features

The Cloud class offers these key functionalities:

```python
from tinytuya import Cloud

# Initialize with your credentials from Tuya IoT platform
cloud = Cloud(
    apiRegion="your-region", 
    apiKey="your-api-key", 
    apiSecret="your-api-secret", 
    apiDeviceID="your-device-id"  # Optional
)

# Get all your devices
devices = cloud.getDevices()

# Control a device through the cloud
cloud.sendCommand(device_id, commands)

# Get device status
status = cloud.getDeviceStatus(device_id)

# Get device information
device_info = cloud.getDeviceInfo(device_id)
```

## Examples of Cloud API Functions

- `getDevices()` - Get all devices associated with your account
- `getDeviceInfo(device_id)` - Get detailed device information
- `getDeviceStatus(device_id)` - Get current device status 
- `getDeviceLogs(device_id)` - Get device operation logs
- `sendCommand(device_id, commands)` - Send commands to control device
- `setDeviceName(device_id, name)` - Update device name
- `getDeviceProperties(device_id)` - Get device properties

## Cloud API vs Local Control

| Cloud API | Local Control |
|-----------|---------------|
| Requires internet connection | Works without internet |
| More reliable connectivity | Faster response time |
| Works with devices anywhere | Device must be on local network |
| Requires Tuya IoT account and API keys | Only needs device ID and local key |
| Has rate limits | No API call limits |
| More device capabilities exposed | Limited to local protocol capabilities |

## Example: Using Cloud API for KKT Kolbe Hood

```python
import tinytuya

# Create cloud connection
cloud = tinytuya.Cloud(
    apiRegion="eu",  # Use your region
    apiKey="your-api-key", 
    apiSecret="your-api-secret"
)

# Find your KKT Kolbe hood in your devices
devices = cloud.getDevices()
for device in devices:
    if "KKT" in device.get("name", ""):
        print(f"Found KKT device: {device['name']} (ID: {device['id']})")

# Get hood status
hood_id = "your_device_id_here"  # Replace with your device ID
status = cloud.getDeviceStatus(hood_id)
print(f"Hood status: {status}")

# Turn on the hood
commands = {"commands": [{"code": "switch", "value": True}]}
cloud.sendCommand(hood_id, commands)

# Set the fan speed
commands = {"commands": [{"code": "fan_speed_enum", "value": "middle"}]}
cloud.sendCommand(hood_id, commands)
```

## Conclusion

Yes, tinytuya can be used to access the Tuya web/cloud API for controlling KKT Kolbe devices. The library provides a comprehensive set of functions for both local control and cloud API access, giving you the flexibility to choose the best method for your needs.

The KKT Kolbe integration currently only uses tinytuya's local control capabilities, but you could extend it to use the cloud API as well if needed.