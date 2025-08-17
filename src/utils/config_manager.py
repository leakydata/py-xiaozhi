import json
import uuid
from typing import Any, Dict

from src.utils.logging_config import get_logger
from src.utils.resource_finder import resource_finder

logger = get_logger(__name__)


class ConfigManager:
    """Configuration Manager - Singleton Pattern"""

    _instance = None

    # Default configuration
    DEFAULT_CONFIG = {
        "SYSTEM_OPTIONS": {
            "CLIENT_ID": None,
            "DEVICE_ID": None,
            "NETWORK": {
                "OTA_VERSION_URL": "https://api.tenclass.net/xiaozhi/ota/",
                "WEBSOCKET_URL": None,
                "WEBSOCKET_ACCESS_TOKEN": None,
                "MQTT_INFO": None,
                "ACTIVATION_VERSION": "v2",  # Options: v1, v2
                "AUTHORIZATION_URL": "https://xiaozhi.me/",
            },
        },
        "WAKE_WORD_OPTIONS": {
            "USE_WAKE_WORD": False,
            "MODEL_PATH": "models/vosk-model-small-cn-0.22",
            "WAKE_WORDS": ["xiao zhi", "xiao mei"],
        },
        "CAMERA": {
            "camera_index": 0,
            "frame_width": 640,
            "frame_height": 480,
            "fps": 30,
            "Local_VL_url": "https://open.bigmodel.cn/api/paas/v4/",
            "VLapi_key": "",
            "models": "glm-4v-plus",
        },
        "SHORTCUTS": {
            "ENABLED": True,
            "MANUAL_PRESS": {"modifier": "ctrl", "key": "j", "description": "Hold to talk"},
            "AUTO_TOGGLE": {"modifier": "ctrl", "key": "k", "description": "Auto-chat"},
            "ABORT": {"modifier": "ctrl", "key": "q", "description": "Interrupt chat"},
            "MODE_TOGGLE": {"modifier": "ctrl", "key": "m", "description": "Toggle mode"},
            "WINDOW_TOGGLE": {
                "modifier": "ctrl",
                "key": "w",
                "description": "Show/hide window",
            },
        },
    }

    def __new__(cls):
        """
        Ensure singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize the configuration manager.
        """
        if self._initialized:
            return
        self._initialized = True

        # Initialize configuration file paths
        self._init_config_paths()

        # Ensure necessary directories exist
        self._ensure_required_directories()

        # Load configuration
        self._config = self._load_config()

    def _init_config_paths(self):
        """
        Initialize configuration file paths.
        """
        # Use resource_finder to find or create the configuration directory
        self.config_dir = resource_finder.find_config_dir()
        if not self.config_dir:
            # If the configuration directory is not found, create it in the project root
            project_root = resource_finder.get_project_root()
            self.config_dir = project_root / "config"
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created configuration directory: {self.config_dir.absolute()}")

        self.config_file = self.config_dir / "config.json"

        # Log configuration file paths
        logger.info(f"Configuration directory: {self.config_dir.absolute()}")
        logger.info(f"Configuration file: {self.config_file.absolute()}")

    def _ensure_required_directories(self):
        """
        Ensure necessary directories exist.
        """
        project_root = resource_finder.get_project_root()

        # Create models directory
        models_dir = project_root / "models"
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created models directory: {models_dir.absolute()}")

        # Create cache directory
        cache_dir = project_root / "cache"
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created cache directory: {cache_dir.absolute()}")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration file, or create it if it doesn't exist.
        """
        try:
            # First, try to find the configuration file using resource_finder
            config_file_path = resource_finder.find_file("config/config.json")

            if config_file_path:
                logger.debug(f"Found configuration file using resource_finder: {config_file_path}")
                config = json.loads(config_file_path.read_text(encoding="utf-8"))
                return self._merge_configs(self.DEFAULT_CONFIG, config)

            # If resource_finder doesn't find it, try using the path from the instance variable
            if self.config_file.exists():
                logger.debug(f"Found configuration file using instance path: {self.config_file}")
                config = json.loads(self.config_file.read_text(encoding="utf-8"))
                return self._merge_configs(self.DEFAULT_CONFIG, config)
            else:
                # Create default configuration file
                logger.info("Configuration file not found, creating default configuration.")
                self._save_config(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG.copy()

        except Exception as e:
            logger.error(f"Configuration loading error: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _save_config(self, config: dict) -> bool:
        """
        Save configuration to file.
        """
        try:
            # Ensure the configuration directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Save the configuration file
            self.config_file.write_text(
                json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.debug(f"Configuration saved to: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Configuration saving error: {e}")
            return False

    @staticmethod
    def _merge_configs(default: dict, custom: dict) -> dict:
        """
        Recursively merge configuration dictionaries.
        """
        result = default.copy()
        for key, value in custom.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._merge_configs(result[key], value)
            else:
                result[key] = value
        return result

    def get_config(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        path: Dot-separated configuration path, e.g., "SYSTEM_OPTIONS.NETWORK.MQTT_INFO"
        """
        try:
            value = self._config
            for key in path.split("."):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def update_config(self, path: str, value: Any) -> bool:
        """
        Update a specific configuration item.
        path: Dot-separated configuration path, e.g., "SYSTEM_OPTIONS.NETWORK.MQTT_INFO"
        """
        try:
            current = self._config
            *parts, last = path.split(".")
            for part in parts:
                current = current.setdefault(part, {})
            current[last] = value
            return self._save_config(self._config)
        except Exception as e:
            logger.error(f"Configuration update error {path}: {e}")
            return False

    def reload_config(self) -> bool:
        """
        Reload the configuration file.
        """
        try:
            self._config = self._load_config()
            logger.info("Configuration file reloaded.")
            return True
        except Exception as e:
            logger.error(f"Configuration reload failed: {e}")
            return False

    def generate_uuid(self) -> str:
        """
        Generate a UUID v4.
        """
        return str(uuid.uuid4())

    def initialize_client_id(self):
        """
        Ensure a client ID exists.
        """
        if not self.get_config("SYSTEM_OPTIONS.CLIENT_ID"):
            client_id = self.generate_uuid()
            success = self.update_config("SYSTEM_OPTIONS.CLIENT_ID", client_id)
            if success:
                logger.info(f"Generated new client ID: {client_id}")
            else:
                logger.error("Failed to save new client ID.")

    def initialize_device_id_from_fingerprint(self, device_fingerprint):
        """
        Initialize device ID from device fingerprint.
        """
        if not self.get_config("SYSTEM_OPTIONS.DEVICE_ID"):
            try:
                # Get MAC address from efuse.json as DEVICE_ID
                mac_address = device_fingerprint.get_mac_address_from_efuse()
                if mac_address:
                    success = self.update_config(
                        "SYSTEM_OPTIONS.DEVICE_ID", mac_address
                    )
                    if success:
                        logger.info(f"Got DEVICE_ID from efuse.json: {mac_address}")
                    else:
                        logger.error("Failed to save DEVICE_ID.")
                else:
                    logger.error("Could not get MAC address from efuse.json")
                    # Fallback: get from device fingerprint directly
                    fingerprint = device_fingerprint.generate_fingerprint()
                    mac_from_fingerprint = fingerprint.get("mac_address")
                    if mac_from_fingerprint:
                        success = self.update_config(
                            "SYSTEM_OPTIONS.DEVICE_ID", mac_from_fingerprint
                        )
                        if success:
                            logger.info(
                                f"Using MAC address from fingerprint as DEVICE_ID: "
                                f"{mac_from_fingerprint}"
                            )
                        else:
                            logger.error("Failed to save fallback DEVICE_ID.")
            except Exception as e:
                logger.error(f"Error initializing DEVICE_ID: {e}")

    @classmethod
    def get_instance(cls):
        """
        Get the configuration manager instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
