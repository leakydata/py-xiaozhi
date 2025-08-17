import json

from src.constants.constants import AbortReason, ListeningMode
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Protocol:
    def __init__(self):
        self.session_id = ""
        # Initialize callback functions to None
        self._on_incoming_json = None
        self._on_incoming_audio = None
        self._on_audio_channel_opened = None
        self._on_audio_channel_closed = None
        self._on_network_error = None
        # Add new connection state change callback
        self._on_connection_state_changed = None
        self._on_reconnecting = None

    def on_incoming_json(self, callback):
        """
        Set the JSON message reception callback function.
        """
        self._on_incoming_json = callback

    def on_incoming_audio(self, callback):
        """
        Set the audio data reception callback function.
        """
        self._on_incoming_audio = callback

    def on_audio_channel_opened(self, callback):
        """
        Set the audio channel opened callback function.
        """
        self._on_audio_channel_opened = callback

    def on_audio_channel_closed(self, callback):
        """
        Set the audio channel closed callback function.
        """
        self._on_audio_channel_closed = callback

    def on_network_error(self, callback):
        """
        Set the network error callback function.
        """
        self._on_network_error = callback

    def on_connection_state_changed(self, callback):
        """Set the connection state change callback function.

        Args:
            callback: Callback function, receives parameters (connected: bool, reason: str)
        """
        self._on_connection_state_changed = callback

    def on_reconnecting(self, callback):
        """Set the reconnection attempt callback function.

        Args:
            callback: Callback function, receives parameters (attempt: int, max_attempts: int)
        """
        self._on_reconnecting = callback

    async def send_text(self, message):
        """
        Abstract method for sending text messages, must be implemented in subclasses.
        """
        raise NotImplementedError("The send_text method must be implemented by a subclass")

    async def send_audio(self, data: bytes):
        """
        Abstract method for sending audio data, must be implemented in subclasses.
        """
        raise NotImplementedError("The send_audio method must be implemented by a subclass")

    def is_audio_channel_opened(self) -> bool:
        """
        Abstract method for checking if the audio channel is open, must be implemented in subclasses.
        """
        raise NotImplementedError("The is_audio_channel_opened method must be implemented by a subclass")

    async def open_audio_channel(self) -> bool:
        """
        Abstract method for opening the audio channel, must be implemented in subclasses.
        """
        raise NotImplementedError("The open_audio_channel method must be implemented by a subclass")

    async def close_audio_channel(self):
        """
        Abstract method for closing the audio channel, must be implemented in subclasses.
        """
        raise NotImplementedError("The close_audio_channel method must be implemented by a subclass")

    async def send_abort_speaking(self, reason):
        """
        Send a message to abort speech.
        """
        message = {"session_id": self.session_id, "type": "abort"}
        if reason == AbortReason.WAKE_WORD_DETECTED:
            message["reason"] = "wake_word_detected"
        await self.send_text(json.dumps(message))

    async def send_wake_word_detected(self, wake_word):
        """
        Send a message indicating a wake word was detected.
        """
        message = {
            "session_id": self.session_id,
            "type": "listen",
            "state": "detect",
            "text": wake_word,
        }
        await self.send_text(json.dumps(message))

    async def send_start_listening(self, mode):
        """
        Send a message to start listening.
        """
        mode_map = {
            ListeningMode.REALTIME: "realtime",
            ListeningMode.AUTO_STOP: "auto",
            ListeningMode.MANUAL: "manual",
        }
        message = {
            "session_id": self.session_id,
            "type": "listen",
            "state": "start",
            "mode": mode_map[mode],
        }
        await self.send_text(json.dumps(message))

    async def send_stop_listening(self):
        """
        Send a message to stop listening.
        """
        message = {"session_id": self.session_id, "type": "listen", "state": "stop"}
        await self.send_text(json.dumps(message))

    async def send_iot_descriptors(self, descriptors):
        """
        Send IoT device descriptor information.
        """
        try:
            # Parse descriptor data
            if isinstance(descriptors, str):
                descriptors_data = json.loads(descriptors)
            else:
                descriptors_data = descriptors

            # Check if it is an array
            if not isinstance(descriptors_data, list):
                logger.error("IoT descriptors should be an array")
                return

            # Send a separate message for each descriptor
            for i, descriptor in enumerate(descriptors_data):
                if descriptor is None:
                    logger.error(f"Failed to get IoT descriptor at index {i}")
                    continue

                message = {
                    "session_id": self.session_id,
                    "type": "iot",
                    "update": True,
                    "descriptors": [descriptor],
                }

                try:
                    await self.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(
                        f"Failed to send JSON message for IoT descriptor "
                        f"at index {i}: {e}"
                    )
                    continue

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse IoT descriptors: {e}")
            return

    async def send_iot_states(self, states):
        """
        Send IoT device status information.
        """
        if isinstance(states, str):
            states_data = json.loads(states)
        else:
            states_data = states

        message = {
            "session_id": self.session_id,
            "type": "iot",
            "update": True,
            "states": states_data,
        }
        await self.send_text(json.dumps(message))

    async def send_mcp_message(self, payload):
        """
        Send an MCP message.
        """
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        message = {
            "session_id": self.session_id,
            "type": "mcp",
            "payload": payload_data,
        }

        await self.send_text(json.dumps(message))
