#!/usr/bin/env python3
"""Test script to verify AsyncServiceInfo API usage."""

import asyncio
import sys

def test_asyncserviceinfo_import():
    """Test if AsyncServiceInfo can be imported and check its methods."""
    try:
        from zeroconf import AsyncServiceInfo
        print("✅ AsyncServiceInfo import successful")

        # Check if async_request method exists
        if hasattr(AsyncServiceInfo, 'async_request'):
            print("✅ AsyncServiceInfo.async_request method exists")

            # Get method signature
            import inspect
            sig = inspect.signature(AsyncServiceInfo.async_request)
            print(f"📋 Method signature: async_request{sig}")

            # Check parameters
            params = list(sig.parameters.keys())
            print(f"📋 Parameters: {params}")

            return True
        else:
            print("❌ AsyncServiceInfo.async_request method does NOT exist")
            print("📋 Available methods:")
            methods = [m for m in dir(AsyncServiceInfo) if not m.startswith('_')]
            for method in methods:
                print(f"   - {method}")
            return False

    except ImportError as e:
        print(f"❌ AsyncServiceInfo import failed: {e}")
        return False

def test_alternative_apis():
    """Test alternative AsyncServiceInfo APIs."""
    try:
        from zeroconf import AsyncServiceInfo

        # Check for other async methods
        async_methods = [m for m in dir(AsyncServiceInfo) if 'async' in m.lower() and not m.startswith('_')]
        print(f"📋 Available async methods: {async_methods}")

        # Check constructors
        if hasattr(AsyncServiceInfo, '__init__'):
            import inspect
            sig = inspect.signature(AsyncServiceInfo.__init__)
            print(f"📋 Constructor signature: __init__{sig}")

    except Exception as e:
        print(f"❌ Error checking alternative APIs: {e}")

if __name__ == "__main__":
    print("🔍 Testing AsyncServiceInfo API usage...")
    print("=" * 50)

    success = test_asyncserviceinfo_import()

    if not success:
        print("\n🔧 Checking alternative APIs...")
        test_alternative_apis()

    print("=" * 50)
    print("✅ Test completed" if success else "❌ Test failed - API needs correction")