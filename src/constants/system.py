# System constant definitions
from enum import Enum


class InitializationStage(Enum):
    """
    Initialization stage enumeration.
    """



    DEVICE_FINGERPRINT = "Stage 1: Device Identity Preparation"
    CONFIG_MANAGEMENT = "Stage 2: Configuration Management Initialization"
    OTA_CONFIG = "Stage 3: OTA Configuration Retrieval"
    ACTIVATION = "Stage 4: Activation Process"


class SystemConstants:
    """
    System constants.
    """

    # Application information
    APP_NAME = "py-xiaozhi"
    APP_VERSION = "2.0.0"
    BOARD_TYPE = "bread-compact-wifi"

    # Default timeout settings
    DEFAULT_TIMEOUT = 10
    ACTIVATION_MAX_RETRIES = 60
    ACTIVATION_RETRY_INTERVAL = 5

    # Filename constants
    CONFIG_FILE = "config.json"
    EFUSE_FILE = "efuse.json"
