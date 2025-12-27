"""Helper modules for KKT Kolbe integration."""
from .validation import (
    is_valid_ip,
    is_valid_device_id,
    is_valid_local_key,
    is_private_ip,
    validate_manual_input,
    validate_api_credentials,
    validate_local_key_input,
)
from .device_detection import (
    detect_device_type_from_api,
    detect_device_type_from_device_id,
    detect_device_type_from_product_key,
    get_device_type_options,
    enrich_device_info,
)
from .entity_factory import (
    get_entity_lookup_key,
    is_advanced_entities_enabled,
    create_entities_from_config,
    create_single_entity_from_config,
    async_setup_platform_entities,
    get_coordinator_from_entry,
    get_device_info_from_entry,
)
from .schemas import (
    # Constants
    API_ENDPOINTS,
    API_ENDPOINT_OPTIONS,
    DEFAULT_API_ENDPOINT,
    # Schema generators
    get_manual_schema,
    get_authentication_schema,
    get_settings_schema,
    get_api_credentials_schema,
    get_device_selection_schema,
    get_smart_discovery_schema,
    get_confirmation_schema,
    get_reconfigure_schemas,
    get_reconfigure_menu_schema,
    get_reconfigure_connection_schema,
    get_reconfigure_device_type_schema,
    get_reconfigure_api_schema,
    get_reconfigure_all_schema,
    get_options_schema,
    get_zeroconf_authenticate_schema,
)

__all__ = [
    # Validation
    "is_valid_ip",
    "is_valid_device_id",
    "is_valid_local_key",
    "is_private_ip",
    "validate_manual_input",
    "validate_api_credentials",
    "validate_local_key_input",
    # Device Detection
    "detect_device_type_from_api",
    "detect_device_type_from_device_id",
    "detect_device_type_from_product_key",
    "get_device_type_options",
    "enrich_device_info",
    # Entity Factory
    "get_entity_lookup_key",
    "is_advanced_entities_enabled",
    "create_entities_from_config",
    "create_single_entity_from_config",
    "async_setup_platform_entities",
    "get_coordinator_from_entry",
    "get_device_info_from_entry",
    # Schema Constants
    "API_ENDPOINTS",
    "API_ENDPOINT_OPTIONS",
    "DEFAULT_API_ENDPOINT",
    # Schema Generators
    "get_manual_schema",
    "get_authentication_schema",
    "get_settings_schema",
    "get_api_credentials_schema",
    "get_device_selection_schema",
    "get_smart_discovery_schema",
    "get_confirmation_schema",
    "get_reconfigure_schemas",
    "get_reconfigure_menu_schema",
    "get_reconfigure_connection_schema",
    "get_reconfigure_device_type_schema",
    "get_reconfigure_api_schema",
    "get_reconfigure_all_schema",
    "get_options_schema",
    "get_zeroconf_authenticate_schema",
]
