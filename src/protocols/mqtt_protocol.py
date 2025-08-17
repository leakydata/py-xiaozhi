import asyncio
import json
import socket
import threading
import time

import paho.mqtt.client as mqtt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from src.constants.constants import AudioConfig
from src.protocols.protocol import Protocol
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

# Configure logging
logger = get_logger(__name__)


class MqttProtocol(Protocol):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.config = ConfigManager.get_instance()
        self.mqtt_client = None
        self.udp_socket = None
        self.udp_thread = None
        self.udp_running = False
        self.connected = False

        # Connection status monitoring
        self._is_closing = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 0  # Default no reconnect
        self._auto_reconnect_enabled = False  # Default disable auto-reconnect
        self._connection_monitor_task = None
        self._last_activity_time = None
        self._keep_alive_interval = 60  # MQTT keep-alive interval (seconds)
        self._connection_timeout = 120  # Connection timeout detection (seconds)

        # MQTT configuration
        self.endpoint = None
        self.client_id = None
        self.username = None
        self.password = None
        self.publish_topic = None
        self.subscribe_topic = None

        # UDP configuration
        self.udp_server = ""
        self.udp_port = 0
        self.aes_key = None
        self.aes_nonce = None
        self.local_sequence = 0
        self.remote_sequence = 0

        # Events
        self.server_hello_event = asyncio.Event()

    def _parse_endpoint(self, endpoint: str) -> tuple[str, int]:
        """
        Parse the endpoint string to extract host and port.
        
        Args:
            endpoint: endpoint string, format can be:
                     - "hostname" (uses default port 8883)
                     - "hostname:port" (uses specified port)
        
        Returns:
            tuple: (host, port) hostname and port number
        """
        if not endpoint:
            raise ValueError("endpoint cannot be empty")
        
        # Check if port is included
        if ":" in endpoint:
            host, port_str = endpoint.rsplit(":", 1)
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError(f"Port number must be between 1-65535: {port}")
            except ValueError as e:
                raise ValueError(f"Invalid port number: {port_str}") from e
        else:
            # No port specified, use default port 8883
            host = endpoint
            port = 8883
        
        return host, port

    async def connect(self):
        """
        Connect to the MQTT server.
        """
        if self._is_closing:
            logger.warning("Connection is closing, canceling new connection attempt")
            return False

        # Reset hello event
        self.server_hello_event = asyncio.Event()

        # First, try to get MQTT configuration
        try:
            # Try to get MQTT configuration from OTA server
            mqtt_config = self.config.get_config("SYSTEM_OPTIONS.NETWORK.MQTT_INFO")

            print(mqtt_config)

            # Update MQTT configuration
            self.endpoint = mqtt_config.get("endpoint")
            self.client_id = mqtt_config.get("client_id")
            self.username = mqtt_config.get("username")
            self.password = mqtt_config.get("password")
            self.publish_topic = mqtt_config.get("publish_topic")
            self.subscribe_topic = mqtt_config.get("subscribe_topic")

            logger.info(f"MQTT configuration obtained from OTA server: {self.endpoint}")
        except Exception as e:
            logger.warning(f"Failed to get MQTT configuration from OTA server: {e}")

        # Validate MQTT configuration
        if (
            not self.endpoint
            or not self.username
            or not self.password
            or not self.publish_topic
        ):
            logger.error("MQTT configuration is incomplete")
            if self._on_network_error:
                await self._on_network_error("MQTT configuration is incomplete")
            return False
        
        # subscribe_topic can be the string "null", needs special handling
        if self.subscribe_topic == "null":
            self.subscribe_topic = None
            logger.info("Subscription topic is null, will not subscribe to any topic")

        # If an MQTT client already exists, disconnect it first
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MQTT client: {e}")

        # Parse endpoint to extract host and port
        try:
            host, port = self._parse_endpoint(self.endpoint)
            use_tls = port == 8883  # Use TLS only when using port 8883
            
            logger.info(f"Parsed endpoint: {self.endpoint} -> Host: {host}, Port: {port}, Use TLS: {use_tls}")
        except ValueError as e:
            logger.error(f"Failed to parse endpoint: {e}")
            if self._on_network_error:
                await self._on_network_error(f"Failed to parse endpoint: {e}")
            return False

        # Create a new MQTT client
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.username_pw_set(self.username, self.password)

        # Configure TLS encrypted connection based on port
        if use_tls:
            try:
                self.mqtt_client.tls_set(
                    ca_certs=None,
                    certfile=None,
                    keyfile=None,
                    cert_reqs=mqtt.ssl.CERT_REQUIRED,
                    tls_version=mqtt.ssl.PROTOCOL_TLS,
                )
                logger.info("TLS encrypted connection configured")
            except Exception as e:
                logger.error(f"TLS configuration failed, cannot securely connect to MQTT server: {e}")
                if self._on_network_error:
                    await self._on_network_error(f"TLS configuration failed: {str(e)}")
                return False
        else:
            logger.info("Using non-TLS connection")

        # Create connection Future
        connect_future = self.loop.create_future()

        def on_connect_callback(client, userdata, flags, rc, properties=None):
            if rc == 0:
                logger.info("Connected to MQTT server")
                self._last_activity_time = time.time()
                self.loop.call_soon_threadsafe(lambda: connect_future.set_result(True))
            else:
                logger.error(f"Failed to connect to MQTT server, return code: {rc}")
                self.loop.call_soon_threadsafe(
                    lambda: connect_future.set_exception(
                        Exception(f"Failed to connect to MQTT server, return code: {rc}")
                    )
                )

        def on_message_callback(client, userdata, msg):
            try:
                self._last_activity_time = time.time()  # Update activity time
                payload = msg.payload.decode("utf-8")
                self._handle_mqtt_message(payload)
            except Exception as e:
                logger.error(f"Error processing MQTT message: {e}")

        def on_disconnect_callback(client, userdata, rc):
            """MQTT disconnect callback.

            Args:
                client: MQTT client instance
                userdata: User data
                rc: Return code (0=normal disconnect, >0=abnormal disconnect)
            """
            try:
                if rc == 0:
                    logger.info("MQTT connection closed normally")
                else:
                    logger.warning(f"MQTT connection closed abnormally, return code: {rc}")

                was_connected = self.connected
                self.connected = False

                # Notify connection state change
                if self._on_connection_state_changed and was_connected:
                    reason = "Normal disconnect" if rc == 0 else f"Abnormal disconnect (rc={rc})"
                    self.loop.call_soon_threadsafe(
                        lambda: self._on_connection_state_changed(False, reason)
                    )

                # Stop UDP receiver thread
                self._stop_udp_receiver()

                # Only attempt to reconnect on abnormal disconnect and if auto-reconnect is enabled
                if (
                    rc != 0
                    and not self._is_closing
                    and self._auto_reconnect_enabled
                    and self._reconnect_attempts < self._max_reconnect_attempts
                ):
                    # Schedule reconnect in the event loop
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(
                            self._attempt_reconnect(f"MQTT disconnect (rc={rc})")
                        )
                    )
                else:
                    # Notify audio channel closed
                    if self._on_audio_channel_closed:
                        asyncio.run_coroutine_threadsafe(
                            self._on_audio_channel_closed(), self.loop
                        )

                    # Notify network error
                    if rc != 0 and self._on_network_error:
                        error_msg = f"MQTT connection disconnected: {rc}"
                        if (
                            self._auto_reconnect_enabled
                            and self._reconnect_attempts >= self._max_reconnect_attempts
                        ):
                            error_msg += " (reconnect failed)"
                        self.loop.call_soon_threadsafe(
                            lambda: self._on_network_error(error_msg)
                        )

            except Exception as e:
                logger.error(f"Failed to handle MQTT disconnection: {e}")

        def on_publish_callback(client, userdata, mid):
            """
            MQTT message publish callback.
            """
            self._last_activity_time = time.time()  # Update activity time

        def on_subscribe_callback(client, userdata, mid, granted_qos):
            """
            MQTT subscribe callback.
            """
            logger.info(f"Successfully subscribed to topic: {self.subscribe_topic}")
            self._last_activity_time = time.time()  # Update activity time

        # Set callbacks
        self.mqtt_client.on_connect = on_connect_callback
        self.mqtt_client.on_message = on_message_callback
        self.mqtt_client.on_disconnect = on_disconnect_callback
        self.mqtt_client.on_publish = on_publish_callback
        self.mqtt_client.on_subscribe = on_subscribe_callback

        try:
            # Connect to MQTT server, configure keep-alive interval
            logger.info(f"Connecting to MQTT server: {host}:{port}")
            self.mqtt_client.connect_async(
                host, port, keepalive=self._keep_alive_interval
            )
            self.mqtt_client.loop_start()

            # Wait for connection to complete
            await asyncio.wait_for(connect_future, timeout=10.0)

            # Subscribe to topic
            if self.subscribe_topic:
                self.mqtt_client.subscribe(self.subscribe_topic, qos=1)

            # Start connection monitor
            self._start_connection_monitor()

            # Send hello message
            hello_message = {
                "type": "hello",
                "version": 3,
                "features": {
                    "mcp": True,
                },
                "transport": "udp",
                "audio_params": {
                    "format": "opus",
                    "sample_rate": AudioConfig.INPUT_SAMPLE_RATE,
                    "channels": AudioConfig.CHANNELS,
                    "frame_duration": AudioConfig.FRAME_DURATION,
                },
            }

            # Send message and wait for response
            if not await self.send_text(json.dumps(hello_message)):
                logger.error("Failed to send hello message")
                return False

            try:
                await asyncio.wait_for(self.server_hello_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for server hello message")
                if self._on_network_error:
                    await self._on_network_error("Timeout waiting for response")
                return False

            # Create UDP socket
            try:
                if self.udp_socket:
                    self.udp_socket.close()

                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.settimeout(0.5)

                # Start UDP receiver thread
                if self.udp_thread and self.udp_thread.is_alive():
                    self.udp_running = False
                    self.udp_thread.join(1.0)

                self.udp_running = True
                self.udp_thread = threading.Thread(target=self._udp_receive_thread)
                self.udp_thread.daemon = True
                self.udp_thread.start()

                self.connected = True
                self._reconnect_attempts = 0  # Reset reconnect counter

                # Notify connection state change
                if self._on_connection_state_changed:
                    self._on_connection_state_changed(True, "Connection successful")

                return True
            except Exception as e:
                logger.error(f"Failed to create UDP socket: {e}")
                if self._on_network_error:
                    await self._on_network_error(f"Failed to create UDP connection: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to MQTT server: {e}")
            if self._on_network_error:
                await self._on_network_error(f"Failed to connect to MQTT server: {e}")
            return False

    def _handle_mqtt_message(self, payload):
        """
        Handle MQTT message.
        """
        try:
            data = json.loads(payload)
            msg_type = data.get("type")

            if msg_type == "goodbye":
                # Handle goodbye message
                session_id = data.get("session_id")
                if not session_id or session_id == self.session_id:
                    # Perform cleanup in the main event loop
                    asyncio.run_coroutine_threadsafe(self._handle_goodbye(), self.loop)
                return

            elif msg_type == "hello":
                print("Server connection returns initial configuration", data)
                # Handle server hello response
                transport = data.get("transport")
                if transport != "udp":
                    logger.error(f"Unsupported transport method: {transport}")
                    return

                # Get session ID
                self.session_id = data.get("session_id", "")

                # Get UDP configuration
                udp = data.get("udp")
                if not udp:
                    logger.error("UDP configuration missing")
                    return

                self.udp_server = udp.get("server")
                self.udp_port = udp.get("port")
                self.aes_key = udp.get("key")
                self.aes_nonce = udp.get("nonce")

                # Reset sequence numbers
                self.local_sequence = 0
                self.remote_sequence = 0

                logger.info(
                    f"Received server hello response, UDP server: {self.udp_server}:{self.udp_port}"
                )

                # Set hello event
                self.loop.call_soon_threadsafe(self.server_hello_event.set)

                # Trigger audio channel opened callback
                if self._on_audio_channel_opened:
                    self.loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self._on_audio_channel_opened())
                    )

            else:
                # Handle other JSON messages
                if self._on_incoming_json:

                    def process_json(json_data=data):
                        if asyncio.iscoroutinefunction(self._on_incoming_json):
                            coro = self._on_incoming_json(json_data)
                            if coro is not None:
                                asyncio.create_task(coro)
                        else:
                            self._on_incoming_json(json_data)

                    self.loop.call_soon_threadsafe(process_json)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON data: {payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _udp_receive_thread(self):
        """UDP receive thread.

        Reference implementation in audio_player.py
        """
        logger.info(
            f"UDP receive thread started, listening for data from {self.udp_server}:{self.udp_port}"
        )

        self.udp_running = True
        debug_counter = 0

        while self.udp_running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                debug_counter += 1

                try:
                    # Validate packet
                    if len(data) < 16:  # At least 16 bytes for nonce
                        logger.error(f"Invalid audio packet size: {len(data)}")
                        continue

                    # Separate nonce and encrypted data
                    received_nonce = data[:16]
                    encrypted_audio = data[16:]

                    # Decrypt using AES-CTR
                    decrypted = self.aes_ctr_decrypt(
                        bytes.fromhex(self.aes_key), received_nonce, encrypted_audio
                    )

                    # Debug information
                    if debug_counter % 100 == 0:
                        logger.debug(
                            f"Decrypted audio packet #{debug_counter}, size: {len(decrypted)} bytes"
                        )

                    # Process decrypted audio data
                    if self._on_incoming_audio:

                        def process_audio(audio_data=decrypted):
                            if asyncio.iscoroutinefunction(self._on_incoming_audio):
                                coro = self._on_incoming_audio(audio_data)
                                if coro is not None:
                                    asyncio.create_task(coro)
                            else:
                                self._on_incoming_audio(audio_data)

                        self.loop.call_soon_threadsafe(process_audio)

                except Exception as e:
                    logger.error(f"Error processing audio packet: {e}")
                    continue

            except socket.timeout:
                # Timeout is normal, continue loop
                pass
            except Exception as e:
                logger.error(f"UDP receive thread error: {e}")
                if not self.udp_running:
                    break
                time.sleep(0.1)  # Avoid excessive CPU consumption in case of error

        logger.info("UDP receive thread stopped")

    async def send_text(self, message):
        """
        Send text message.
        """
        if not self.mqtt_client:
            logger.error("MQTT client not initialized")
            return False

        try:
            result = self.mqtt_client.publish(self.publish_topic, message)
            result.wait_for_publish()
            return True
        except Exception as e:
            logger.error(f"Failed to send MQTT message: {e}")
            if self._on_network_error:
                await self._on_network_error(f"Failed to send MQTT message: {e}")
            return False

    async def send_audio(self, audio_data):
        """Send audio data.

        Reference implementation in audio_sender.py
        """
        if not self.udp_socket or not self.udp_server or not self.udp_port:
            logger.error("UDP channel not initialized")
            return False

        try:
            # Generate new nonce (similar to implementation in audio_sender.py)
            # Format: 0x01 (1 byte) + 0x00 (3 bytes) + length (2 bytes) + original nonce (8 bytes) + sequence number (8 bytes)
            self.local_sequence = (self.local_sequence + 1) & 0xFFFFFFFF
            new_nonce = (
                self.aes_nonce[:4]  # Fixed prefix
                + format(len(audio_data), "04x")  # Data length
                + self.aes_nonce[8:24]  # Original nonce
                + format(self.local_sequence, "08x")  # Sequence number
            )

            encrypt_encoded_data = self.aes_ctr_encrypt(
                bytes.fromhex(self.aes_key), bytes.fromhex(new_nonce), bytes(audio_data)
            )

            # Concatenate nonce and ciphertext
            packet = bytes.fromhex(new_nonce) + encrypt_encoded_data

            # Send packet
            self.udp_socket.sendto(packet, (self.udp_server, self.udp_port))

            # Log every 10 packets sent
            if self.local_sequence % 10 == 0:
                logger.info(
                    f"Sent audio packet, sequence: {self.local_sequence}, destination: "
                    f"{self.udp_server}:{self.udp_port}"
                )

            self.local_sequence += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send audio data: {e}")
            if self._on_network_error:
                asyncio.create_task(self._on_network_error(f"Failed to send audio data: {e}"))
            return False

    async def open_audio_channel(self):
        """
        Open audio channel.
        """
        if not self.connected:
            return await self.connect()
        return True

    async def close_audio_channel(self):
        """
        Close audio channel.
        """
        self._is_closing = True

        try:
            # If there is a session ID, send a goodbye message
            if self.session_id:
                goodbye_msg = {"type": "goodbye", "session_id": self.session_id}
                await self.send_text(json.dumps(goodbye_msg))

            # Handle goodbye
            await self._handle_goodbye()

        except Exception as e:
            logger.error(f"Error closing audio channel: {e}")
            # Ensure callback is called even if there is an error
            if self._on_audio_channel_closed:
                await self._on_audio_channel_closed()
        finally:
            self._is_closing = False

    def is_audio_channel_opened(self) -> bool:
        """Check if the audio channel is open.

        More accurately checks the connection status, including the actual state of MQTT and UDP.
        """
        if not self.connected or self._is_closing:
            return False

        # Check MQTT connection status
        if not self.mqtt_client or not self.mqtt_client.is_connected():
            return False

        # Check UDP connection status
        return self.udp_socket is not None and self.udp_running

    def aes_ctr_encrypt(self, key, nonce, plaintext):
        """AES-CTR mode encryption function
        Args:
            key: encryption key in bytes format
            nonce: initial vector in bytes format
            plaintext: original data to be encrypted
        Returns:
            encrypted data in bytes format
        """
        cipher = Cipher(
            algorithms.AES(key), modes.CTR(nonce), backend=default_backend()
        )
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()

    def aes_ctr_decrypt(self, key, nonce, ciphertext):
        """AES-CTR mode decryption function
        Args:
            key: decryption key in bytes format
            nonce: initial vector in bytes format (must be the same as used for encryption)
            ciphertext: encrypted data in bytes format
        Returns:
            decrypted original data in bytes format
        """
        cipher = Cipher(
            algorithms.AES(key), modes.CTR(nonce), backend=default_backend()
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext

    async def _handle_goodbye(self):
        """
        Handle goodbye message.
        """
        try:
            # Stop UDP receive thread
            if self.udp_thread and self.udp_thread.is_alive():
                self.udp_running = False
                self.udp_thread.join(1.0)
                self.udp_thread = None
            logger.info("UDP receive thread stopped")

            # Close UDP socket
            if self.udp_socket:
                try:
                    self.udp_socket.close()
                except Exception as e:
                    logger.error(f"Failed to close UDP socket: {e}")
                self.udp_socket = None

            # Stop MQTT client
            if self.mqtt_client:
                try:
                    self.mqtt_client.loop_stop()
                    self.mqtt_client.disconnect()
                    self.mqtt_client.loop_forever()  # Ensure disconnection is complete
                except Exception as e:
                    logger.error(f"Failed to disconnect MQTT: {e}")
                self.mqtt_client = None

            # Reset all states
            self.connected = False
            self.session_id = None
            self.local_sequence = 0
            self.remote_sequence = 0
            self.udp_server = ""
            self.udp_port = 0
            self.aes_key = None
            self.aes_nonce = None

            # Call audio channel closed callback
            if self._on_audio_channel_closed:
                await self._on_audio_channel_closed()

        except Exception as e:
            logger.error(f"Error handling goodbye message: {e}")

    def _stop_udp_receiver(self):
        """
        Stop UDP receive thread and close UDP socket.
        """
        # Close UDP receive thread
        if (
            hasattr(self, "udp_thread")
            and self.udp_thread
            and self.udp_thread.is_alive()
        ):
            self.udp_running = False
            try:
                self.udp_thread.join(1.0)
            except RuntimeError:
                pass  # Handle case where thread has already terminated

        # Close UDP socket
        if hasattr(self, "udp_socket") and self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception as e:
                logger.error(f"Failed to close UDP socket: {e}")

    def __del__(self):
        """
        Destructor, clean up resources.
        """
        # Stop UDP reception related resources
        self._stop_udp_receiver()

        # Close MQTT client
        if hasattr(self, "mqtt_client") and self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                self.mqtt_client.loop_forever()  # Ensure disconnection is complete
            except Exception as e:
                logger.error(f"Failed to disconnect MQTT: {e}")

    def _start_connection_monitor(self):
        """
        Start connection monitoring task.
        """
        if (
            self._connection_monitor_task is None
            or self._connection_monitor_task.done()
        ):
            self._connection_monitor_task = asyncio.create_task(
                self._connection_monitor()
            )

    async def _connection_monitor(self):
        """
        Connection health status monitoring.
        """
        try:
            while self.connected and not self._is_closing:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check MQTT connection status
                if self.mqtt_client and not self.mqtt_client.is_connected():
                    logger.warning("MQTT connection loss detected")
                    await self._handle_connection_loss("MQTT connection check failed")
                    break

                # Check last activity time (timeout detection)
                if self._last_activity_time:
                    time_since_activity = time.time() - self._last_activity_time
                    if time_since_activity > self._connection_timeout:
                        logger.warning(
                            f"Connection timeout, last activity: {time_since_activity:.1f} seconds ago"
                        )
                        await self._handle_connection_loss("Connection timeout")
                        break

        except asyncio.CancelledError:
            logger.debug("MQTT connection monitoring task was canceled")
        except Exception as e:
            logger.error(f"MQTT connection monitoring exception: {e}")

    async def _handle_connection_loss(self, reason: str):
        """
        Handle connection loss.
        """
        logger.warning(f"MQTT connection lost: {reason}")

        # Update connection status
        was_connected = self.connected
        self.connected = False

        # Notify connection state change
        if self._on_connection_state_changed and was_connected:
            try:
                self._on_connection_state_changed(False, reason)
            except Exception as e:
                logger.error(f"Failed to call connection state change callback: {e}")

        # Clean up connection
        await self._cleanup_connection()

        # Notify audio channel closed
        if self._on_audio_channel_closed:
            try:
                await self._on_audio_channel_closed()
            except Exception as e:
                logger.error(f"Failed to call audio channel closed callback: {e}")

        # Only attempt to reconnect if auto-reconnect is enabled and not manually closed
        if (
            not self._is_closing
            and self._auto_reconnect_enabled
            and self._reconnect_attempts < self._max_reconnect_attempts
        ):
            await self._attempt_reconnect(reason)
        else:
            # Notify network error
            if self._on_network_error:
                if (
                    self._auto_reconnect_enabled
                    and self._reconnect_attempts >= self._max_reconnect_attempts
                ):
                    await self._on_network_error(f"MQTT connection lost and reconnect failed: {reason}")
                else:
                    await self._on_network_error(f"MQTT connection lost: {reason}")

    async def _attempt_reconnect(self, original_reason: str):
        """
        Attempt auto-reconnect.
        """
        self._reconnect_attempts += 1

        # Notify starting reconnect
        if self._on_reconnecting:
            try:
                self._on_reconnecting(
                    self._reconnect_attempts, self._max_reconnect_attempts
                )
            except Exception as e:
                logger.error(f"Failed to call reconnecting callback: {e}")

        logger.info(
            f"Attempting MQTT auto-reconnect ({self._reconnect_attempts}/{self._max_reconnect_attempts})"
        )

        # Wait for a while before reconnecting (exponential backoff)
        await asyncio.sleep(min(self._reconnect_attempts * 2, 30))

        try:
            success = await self.connect()
            if success:
                logger.info("MQTT auto-reconnect successful")
                # Notify connection state change
                if self._on_connection_state_changed:
                    self._on_connection_state_changed(True, "Reconnect successful")
            else:
                logger.warning(
                    f"MQTT auto-reconnect failed ({self._reconnect_attempts}/{self._max_reconnect_attempts})"
                )
                # If retries are still possible, do not report an error immediately
                if self._reconnect_attempts >= self._max_reconnect_attempts:
                    if self._on_network_error:
                        await self._on_network_error(
                            f"MQTT reconnect failed, max retries reached: {original_reason}"
                        )
        except Exception as e:
            logger.error(f"Error during MQTT reconnect process: {e}")
            if self._reconnect_attempts >= self._max_reconnect_attempts:
                if self._on_network_error:
                    await self._on_network_error(f"MQTT reconnect exception: {str(e)}")

    def enable_auto_reconnect(self, enabled: bool = True, max_attempts: int = 5):
        """Enable or disable auto-reconnect feature.

        Args:
            enabled: Whether to enable auto-reconnect
            max_attempts: Maximum number of reconnect attempts
        """
        self._auto_reconnect_enabled = enabled
        if enabled:
            self._max_reconnect_attempts = max_attempts
            logger.info(f"Enabled MQTT auto-reconnect, max attempts: {max_attempts}")
        else:
            self._max_reconnect_attempts = 0
            logger.info("Disabled MQTT auto-reconnect")

    def get_connection_info(self) -> dict:
        """Get connection information.

        Returns:
            dict: A dictionary containing connection status, reconnect attempts, etc.
        """
        return {
            "connected": self.connected,
            "mqtt_connected": (
                self.mqtt_client.is_connected() if self.mqtt_client else False
            ),
            "is_closing": self._is_closing,
            "auto_reconnect_enabled": self._auto_reconnect_enabled,
            "reconnect_attempts": self._reconnect_attempts,
            "max_reconnect_attempts": self._max_reconnect_attempts,
            "last_activity_time": self._last_activity_time,
            "keep_alive_interval": self._keep_alive_interval,
            "connection_timeout": self._connection_timeout,
            "mqtt_endpoint": self.endpoint,
            "udp_server": (
                f"{self.udp_server}:{self.udp_port}" if self.udp_server else None
            ),
            "session_id": self.session_id,
        }

    async def _cleanup_connection(self):
        """
        Clean up connection-related resources.
        """
        self.connected = False

        # Cancel connection monitoring task
        if self._connection_monitor_task and not self._connection_monitor_task.done():
            self._connection_monitor_task.cancel()
            try:
                await self._connection_monitor_task
            except asyncio.CancelledError:
                pass

        # Stop UDP receive thread
        self._stop_udp_receiver()

        # Stop MQTT client
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting MQTT: {e}")

        # Reset timestamp
        self._last_activity_time = None
