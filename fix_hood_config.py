#!/usr/bin/env python3
"""
Fix Hood Configuration Script
Run this on Home Assistant server to update Hood IP and enable cloud fallback.

Usage:
  python3 fix_hood_config.py

Or via HA terminal:
  docker exec -it homeassistant python3 /config/custom_components/kkt_kolbe/fix_hood_config.py
"""

import json
import os
import sys
from pathlib import Path

# Configuration
HOOD_DEVICE_ID = "bfbb89aedbb95dd57cawxf"
NEW_IP = "192.168.2.203"

# Find config entries file
CONFIG_PATHS = [
    "/config/.storage/core.config_entries",
    "/homeassistant/.storage/core.config_entries",
    os.path.expanduser("~/.homeassistant/.storage/core.config_entries"),
]

def find_config_file():
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None

def main():
    config_file = find_config_file()
    if not config_file:
        print("❌ Could not find core.config_entries file")
        print("Tried:", CONFIG_PATHS)
        sys.exit(1)

    print(f"📁 Found config file: {config_file}")

    # Create backup
    backup_file = config_file + ".backup"
    with open(config_file, 'r') as f:
        data = json.load(f)

    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Backup created: {backup_file}")

    # Find and update Hood entry
    updated = False
    for entry in data.get("data", {}).get("entries", []):
        if entry.get("domain") != "kkt_kolbe":
            continue

        entry_data = entry.get("data", {})
        device_id = entry_data.get("device_id") or entry_data.get("CONF_DEVICE_ID")

        if device_id == HOOD_DEVICE_ID:
            print(f"\n🔍 Found Hood entry:")
            print(f"   Title: {entry.get('title')}")
            print(f"   Current IP: {entry_data.get('ip_address') or entry_data.get('host')}")
            print(f"   Setup Mode: {entry_data.get('setup_mode')}")

            # Update IP
            if "ip_address" in entry_data:
                entry_data["ip_address"] = NEW_IP
            if "host" in entry_data:
                entry_data["host"] = NEW_IP
            if "CONF_IP_ADDRESS" in entry_data:
                entry_data["CONF_IP_ADDRESS"] = NEW_IP

            # Ensure SmartLife fallback is enabled
            if entry_data.get("setup_mode") == "smartlife":
                entry_data["integration_mode"] = "smartlife"
                print(f"   ✓ SmartLife cloud fallback enabled")
            elif entry_data.get("setup_mode") == "manual":
                # For manual entries, enable hybrid mode if API is available
                if entry_data.get("api_enabled"):
                    entry_data["integration_mode"] = "hybrid"
                    print(f"   ✓ Hybrid mode enabled (local + cloud)")

            print(f"   ✓ New IP: {NEW_IP}")
            updated = True
            break

    if not updated:
        print(f"\n❌ Hood entry not found (device_id: {HOOD_DEVICE_ID})")
        print("\nAvailable KKT Kolbe entries:")
        for entry in data.get("data", {}).get("entries", []):
            if entry.get("domain") == "kkt_kolbe":
                entry_data = entry.get("data", {})
                print(f"  - {entry.get('title')}: {entry_data.get('device_id', 'no device_id')}")
        sys.exit(1)

    # Save updated config
    with open(config_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Configuration updated!")
    print(f"\n⚠️  Restart Home Assistant to apply changes:")
    print(f"   docker restart homeassistant")
    print(f"   # or via HA UI: Settings > System > Restart")

if __name__ == "__main__":
    main()
