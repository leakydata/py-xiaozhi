import hashlib
import hmac
import json
import platform
from pathlib import Path
from typing import Dict, Optional, Tuple

import machineid
import psutil

from src.utils.logging_config import get_logger
from src.utils.resource_finder import find_config_dir

# Get logger
logger = get_logger(__name__)


class DeviceFingerprint:
    """Device Fingerprint Collector - used to generate a unique device identifier"""

    _instance = None

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
        Initialize the device fingerprint collector.
        """
        if self._initialized:
            return
        self._initialized = True

        self.system = platform.system()
        self._efuse_cache: Optional[Dict] = None  # efuse data cache

        # Initialize file paths
        self._init_file_paths()

        # Ensure the efuse file exists and is complete upon initialization
        self._ensure_efuse_file()

    def _init_file_paths(self):
        """
        Initialize file paths.
        """
        config_dir = find_config_dir()
        if config_dir:
            self.efuse_file = config_dir / "efuse.json"
            logger.debug(f"Using config directory: {config_dir}")
        else:
            # Fallback: use a relative path and ensure the directory exists
            config_path = Path("config")
            config_path.mkdir(parents=True, exist_ok=True)
            self.efuse_file = config_path / "efuse.json"
            logger.info(f"Creating config directory: {config_path.absolute()}")

    def get_hostname(self) -> str:
        """
        Get the computer hostname.
        """
        return platform.node()

    def _normalize_mac_address(self, mac_address: str) -> str:
        """Normalize MAC address format to lowercase colon-separated format.

        Args:
            mac_address: The original MAC address, possibly using hyphens, colons, or other separators

        Returns:
            str: The normalized MAC address in the format "00:00:00:00:00:00"
        """
        if not mac_address:
            return mac_address

        # Remove all possible separators, keeping only hexadecimal characters
        clean_mac = "".join(c for c in mac_address if c.isalnum())

        # Ensure the length is 12 characters (hex representation of 6 bytes)
        if len(clean_mac) != 12:
            logger.warning(f"Incorrect MAC address length: {mac_address} -> {clean_mac}")
            return mac_address.lower()

        # Reformat to standard colon-separated format
        formatted_mac = ":".join(clean_mac[i : i + 2] for i in range(0, 12, 2))

        # Convert to lowercase
        return formatted_mac.lower()

    def get_mac_address(self) -> Optional[str]:
        """
        Get the MAC address of the primary network adapter.
        """
        try:
            # Get address information for all network interfaces
            net_if_addrs = psutil.net_if_addrs()

            # Prioritize the MAC address of non-loopback interfaces
            for iface, addrs in net_if_addrs.items():
                # Skip loopback interfaces
                if iface.lower().startswith(("lo", "loopback")):
                    continue

                for snic in addrs:
                    if snic.family == psutil.AF_LINK and snic.address:
                        # Normalize MAC address format
                        normalized_mac = self._normalize_mac_address(snic.address)
                        # Filter out invalid MAC addresses
                        if normalized_mac != "00:00:00:00:00:00":
                            return normalized_mac

            # If no suitable MAC address is found, return None
            logger.warning("No valid MAC address found")
            return None

        except Exception as e:
            logger.error(f"Error getting MAC address: {e}")
            return None

    def get_machine_id(self) -> Optional[str]:
        """
        Get the unique device identifier.
        """
        try:
            return machineid.id()
        except machineid.MachineIdNotFound:
            logger.warning("Machine ID not found")
            return None
        except Exception as e:
            logger.error(f"Error getting machine ID: {e}")
            return None

    def _generate_fresh_fingerprint(self) -> Dict:
        """
        Generate a fresh device fingerprint (not dependent on cache or file).
        """
        return {
            "system": self.system,
            "hostname": self.get_hostname(),
            "mac_address": self.get_mac_address(),
            "machine_id": self.get_machine_id(),
        }

    def generate_fingerprint(self) -> Dict:
        """
        Generate a complete device fingerprint (prioritizing reading from efuse.json).
        """
        # First, try to read the device fingerprint from efuse.json
        if self.efuse_file.exists():
            try:
                efuse_data = self._load_efuse_data()
                if efuse_data.get("device_fingerprint"):
                    logger.debug("Reading device fingerprint from efuse.json")
                    return efuse_data["device_fingerprint"]
            except Exception as e:
                logger.warning(f"Failed to read device fingerprint from efuse.json: {e}")

        # If reading fails or it doesn't exist, generate a new device fingerprint
        logger.info("Generating new device fingerprint")
        return self._generate_fresh_fingerprint()

    def generate_hardware_hash(self) -> str:
        """
        Generate a unique hash based on hardware information.
        """
        fingerprint = self.generate_fingerprint()

        # Extract the most immutable hardware identifiers
        identifiers = []

        # Hostname
        hostname = fingerprint.get("hostname")
        if hostname:
            identifiers.append(hostname)

        # MAC address
        mac_address = fingerprint.get("mac_address")
        if mac_address:
            identifiers.append(mac_address)

        # Machine ID
        machine_id = fingerprint.get("machine_id")
        if machine_id:
            identifiers.append(machine_id)

        # If no identifiers are found, use system information as a fallback
        if not identifiers:
            identifiers.append(self.system)
            logger.warning("No hardware identifiers found, using system information as a fallback")

        # Concatenate all identifiers and calculate the hash
        fingerprint_str = "||".join(identifiers)
        return hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()

    def generate_serial_number(self) -> str:
        """
        Generate device serial number.
        """
        fingerprint = self.generate_fingerprint()

        # Prioritize using the primary network adapter's MAC address to generate the serial number
        mac_address = fingerprint.get("mac_address")

        if not mac_address:
            # If there is no MAC address, use the machine ID or hostname
            machine_id = fingerprint.get("machine_id")
            hostname = fingerprint.get("hostname")

            if machine_id:
                identifier = machine_id[:12]  # Take the first 12 characters
            elif hostname:
                identifier = hostname.replace("-", "").replace("_", "")[:12]
            else:
                identifier = "unknown"

            short_hash = hashlib.md5(identifier.encode()).hexdigest()[:8].upper()
            return f"SN-{short_hash}-{identifier.upper()}"

        # Ensure the MAC address is lowercase and has no colons
        mac_clean = mac_address.lower().replace(":", "")
        short_hash = hashlib.md5(mac_clean.encode()).hexdigest()[:8].upper()
        serial_number = f"SN-{short_hash}-{mac_clean}"
        return serial_number

    def _ensure_efuse_file(self):
        """
        Ensure the efuse file exists and contains complete information.
        """
        logger.info(f"Checking efuse file: {self.efuse_file.absolute()}")

        # First, generate the device fingerprint (this ensures hardware information is available)
        fingerprint = self._generate_fresh_fingerprint()
        mac_address = fingerprint.get("mac_address")

        if not self.efuse_file.exists():
            logger.info("efuse.json file does not exist, creating a new one")
            self._create_new_efuse_file(fingerprint, mac_address)
        else:
            logger.info("efuse.json file already exists, verifying integrity")
            self._validate_and_fix_efuse_file(fingerprint, mac_address)

    def _create_new_efuse_file(self, fingerprint: Dict, mac_address: Optional[str]):
        """
        Create a new efuse file.
        """
        # Generate serial number and HMAC key
        serial_number = self.generate_serial_number()
        hmac_key = self.generate_hardware_hash()

        logger.info(f"Generated serial number: {serial_number}")
        logger.debug(f"Generated HMAC key: {hmac_key[:8]}...")  # Log only the first 8 characters

        # Create complete efuse data
        efuse_data = {
            "mac_address": mac_address,
            "serial_number": serial_number,
            "hmac_key": hmac_key,
            "activation_status": False,
            "device_fingerprint": fingerprint,
        }

        # Ensure the directory exists
        self.efuse_file.parent.mkdir(parents=True, exist_ok=True)

        # Write data
        success = self._save_efuse_data(efuse_data)
        if success:
            logger.info(f"efuse config file created: {self.efuse_file}")
        else:
            logger.error("Failed to create efuse config file")

    def _validate_and_fix_efuse_file(
        self, fingerprint: Dict, mac_address: Optional[str]
    ):
        """
        Validate and fix the integrity of the efuse file.
        """
        try:
            efuse_data = self._load_efuse_data_from_file()

            # Check if necessary fields exist
            required_fields = [
                "mac_address",
                "serial_number",
                "hmac_key",
                "activation_status",
                "device_fingerprint",
            ]
            missing_fields = [
                field for field in required_fields if field not in efuse_data
            ]

            if missing_fields:
                logger.warning(f"efuse config file is missing fields: {missing_fields}")
                self._fix_missing_fields(
                    efuse_data, missing_fields, fingerprint, mac_address
                )
            else:
                logger.debug("efuse config file integrity check passed")
                # Update cache
                self._efuse_cache = efuse_data

        except Exception as e:
            logger.error(f"Error validating efuse config file: {e}")
            # If validation fails, recreate the file
            logger.info("Recreating efuse config file")
            self._create_new_efuse_file(fingerprint, mac_address)

    def _fix_missing_fields(
        self,
        efuse_data: Dict,
        missing_fields: list,
        fingerprint: Dict,
        mac_address: Optional[str],
    ):
        """
        Fix missing fields.
        """
        for field in missing_fields:
            if field == "device_fingerprint":
                efuse_data[field] = fingerprint
            elif field == "mac_address":
                efuse_data[field] = mac_address
            elif field == "serial_number":
                efuse_data[field] = self.generate_serial_number()
            elif field == "hmac_key":
                efuse_data[field] = self.generate_hardware_hash()
            elif field == "activation_status":
                efuse_data[field] = False

        # Save the fixed data
        success = self._save_efuse_data(efuse_data)
        if success:
            logger.info("efuse config file has been fixed")
        else:
            logger.error("Failed to fix efuse config file")

    def _load_efuse_data_from_file(self) -> Dict:
        """
        Load efuse data directly from the file (without using cache).
        """
        with open(self.efuse_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_efuse_data(self) -> Dict:
        """
        Load efuse data (with cache).
        """
        # If there is a cache, return it directly
        if self._efuse_cache is not None:
            return self._efuse_cache

        try:
            data = self._load_efuse_data_from_file()
            # Cache data
            self._efuse_cache = data
            return data
        except Exception as e:
            logger.error(f"Failed to load efuse data: {e}")
            # Return empty default data, but do not cache it
            return {
                "mac_address": None,
                "serial_number": None,
                "hmac_key": None,
                "activation_status": False,
                "device_fingerprint": {},
            }

    def _save_efuse_data(self, data: Dict) -> bool:
        """
        Save efuse data.
        """
        try:
            # Ensure the directory exists
            self.efuse_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.efuse_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Update cache
            self._efuse_cache = data
            logger.debug(f"efuse data saved to: {self.efuse_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save efuse data: {e}")
            return False

    def ensure_device_identity(self) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Ensure device identity information is loaded - returns serial number, HMAC key, and activation status

        Returns:
            Tuple[Optional[str], Optional[str], bool]: (serial number, HMAC key, activation status)
        """
        # Load efuse data (the file should exist and be complete at this point)
        efuse_data = self._load_efuse_data()

        # Get serial number, HMAC key, and activation status
        serial_number = efuse_data.get("serial_number")
        hmac_key = efuse_data.get("hmac_key")
        is_activated = efuse_data.get("activation_status", False)

        return serial_number, hmac_key, is_activated

    def has_serial_number(self) -> bool:
        """
        Check if there is a serial number.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("serial_number") is not None

    def get_serial_number(self) -> Optional[str]:
        """
        Get the serial number.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("serial_number")

    def get_hmac_key(self) -> Optional[str]:
        """
        Get the HMAC key.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("hmac_key")

    def get_mac_address_from_efuse(self) -> Optional[str]:
        """
        Get the MAC address from efuse.json.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("mac_address")

    def set_activation_status(self, status: bool) -> bool:
        """
        Set the activation status.
        """
        efuse_data = self._load_efuse_data()
        efuse_data["activation_status"] = status
        return self._save_efuse_data(efuse_data)

    def is_activated(self) -> bool:
        """
        Check if the device is activated.
        """
        efuse_data = self._load_efuse_data()
        return efuse_data.get("activation_status", False)

    def generate_hmac(self, challenge: str) -> Optional[str]:
        """
        Generate a signature using the HMAC key.
        """
        if not challenge:
            logger.error("Challenge string cannot be empty")
            return None

        hmac_key = self.get_hmac_key()

        if not hmac_key:
            logger.error("HMAC key not found, cannot generate signature")
            return None

        try:
            # Calculate HMAC-SHA256 signature
            signature = hmac.new(
                hmac_key.encode(), challenge.encode(), hashlib.sha256
            ).hexdigest()

            return signature
        except Exception as e:
            logger.error(f"Failed to generate HMAC signature: {e}")
            return None

    @classmethod
    def get_instance(cls) -> "DeviceFingerprint":
        """
        Get the device fingerprint instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
