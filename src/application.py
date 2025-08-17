import asyncio
import json
import signal
import sys
import threading
from typing import Set

from src.constants.constants import AbortReason, DeviceState, ListeningMode
from src.display import gui_display
from src.mcp.mcp_server import McpServer
from src.protocols.mqtt_protocol import MqttProtocol
from src.protocols.websocket_protocol import WebsocketProtocol
from src.utils.common_utils import handle_verification_code
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger
from src.utils.opus_loader import setup_opus

# Ignore SIGTRAP signal
try:
    if hasattr(signal, "SIGTRAP"):
        signal.signal(signal.SIGTRAP, signal.SIG_IGN)
except (AttributeError, ValueError) as e:
    print(f"Note: Unable to set SIGTRAP handler: {e}")


def handle_sigint(signum, frame):
    app = Application.get_instance()
    if app:
        # Use the event loop to run shutdown
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(app.shutdown())
        except RuntimeError:
            # No running event loop, exit directly
            sys.exit(0)


try:
    signal.signal(signal.SIGINT, handle_sigint)
except (AttributeError, ValueError) as e:
    print(f"Note: Unable to set SIGINT handler: {e}")

setup_opus()

logger = get_logger(__name__)

try:
    import opuslib  # noqa: F401
except Exception as e:
    logger.critical("Failed to import opuslib: %s", e, exc_info=True)
    logger.critical("Please ensure the opus dynamic library is installed correctly or in the correct location")
    sys.exit(1)


class Application:
    """
    Application architecture based on pure asyncio.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = Application()
        return cls._instance

    def __init__(self):
        """
        Initialize the application.
        """
        if Application._instance is not None:
            logger.error("Attempting to create multiple instances of Application")
            raise Exception("Application is a singleton class, please use get_instance() to get an instance")
        Application._instance = self

        logger.debug("Initializing Application instance")

        # Configuration management
        self.config = ConfigManager.get_instance()

        # State management
        self.device_state = DeviceState.IDLE
        self.voice_detected = False
        self.keep_listening = False
        self.aborted = False

        # Asynchronous components
        self.audio_codec = None
        self.protocol = None
        self.display = None
        self.wake_word_detector = None
        # Task management
        self.running = False
        self._main_tasks: Set[asyncio.Task] = set()

        # Command queue - initialized when the event loop is running
        self.command_queue: asyncio.Queue = None

        # Task cancellation event - initialized when the event loop is running
        self._shutdown_event = None

        # Save the event loop of the main thread (set later in the run method)
        self._main_loop = None

        # MCP server
        self.mcp_server = McpServer.get_instance()

        # Message handler mapping
        self._message_handlers = {
            "tts": self._handle_tts_message,
            "stt": self._handle_stt_message,
            "llm": self._handle_llm_message,
            "iot": self._handle_iot_message,
            "mcp": self._handle_mcp_message,
        }

        # Concurrency control locks
        self._state_lock = asyncio.Lock()
        self._abort_lock = asyncio.Lock()

        logger.debug("Application instance initialization complete")

    async def run(self, **kwargs):
        """
        Start the application.
        """
        logger.info("Starting application, parameters: %s", kwargs)

        mode = kwargs.get("mode", "gui")
        protocol = kwargs.get("protocol", "websocket")

        if mode == "gui":
            # GUI mode: requires creating a Qt application and qasync event loop
            return await self._run_gui_mode(protocol)
        else:
            # CLI mode: use standard asyncio
            return await self._run_cli_mode(protocol)

    async def _run_gui_mode(self, protocol: str):
        """
        Run the application in GUI mode.
        """
        try:
            import qasync
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            logger.error("GUI mode requires qasync and PyQt5 libraries, please install: pip install qasync PyQt5")
            return 1

        try:
            # Check if a QApplication instance already exists
            app = QApplication.instance()
            if app is None:
                logger.info("Creating a new QApplication instance")
                app = QApplication(sys.argv)
            else:
                logger.info("Using an existing QApplication instance")

            # Ensure previous event loops are cleaned up
            try:
                current_loop = asyncio.get_event_loop()
                if current_loop and not current_loop.is_closed():
                    logger.debug("Found an existing event loop, preparing to close")
                    # Do not force close, let it finish naturally
            except RuntimeError:
                # No existing loop, this is normal
                pass

            # Create a new qasync event loop
            loop = qasync.QEventLoop(app)
            asyncio.set_event_loop(loop)
            logger.info("qasync event loop has been set")

            # Run the application in the qasync environment
            with loop:
                try:
                    task = self._run_application_core(protocol, "gui")
                    return loop.run_until_complete(task)
                except RuntimeError as e:
                    error_msg = "Event loop stopped before Future completed"
                    if error_msg in str(e):
                        # Normal exit case, the event loop was stopped by QApplication.quit()
                        logger.info("GUI application exited normally")
                        return 0
                    else:
                        # Other runtime errors
                        raise

        except Exception as e:
            logger.error(f"GUI application exited with an exception: {e}", exc_info=True)
            return 1
        finally:
            # Ensure the event loop is properly closed
            try:
                if "loop" in locals():
                    loop.close()
            except Exception:
                pass

    async def _run_cli_mode(self, protocol: str):
        """
        Run the application in CLI mode.
        """
        try:
            return await self._run_application_core(protocol, "cli")
        except Exception as e:
            logger.error(f"CLI application exited with an exception: {e}", exc_info=True)
            return 1

    def _initialize_async_objects(self):
        """
        Initialize asynchronous objects - must be called after the event loop is running.
        """
        logger.debug("Initializing asynchronous objects")
        self.command_queue = asyncio.Queue()
        self._shutdown_event = asyncio.Event()

    async def _run_application_core(self, protocol: str, mode: str):
        """
        Application core execution logic.
        """
        try:
            self.running = True

            # Save the event loop of the main thread
            self._main_loop = asyncio.get_running_loop()

            # Initialize asynchronous objects - must be created after the event loop is running
            self._initialize_async_objects()

            # Initialize components
            await self._initialize_components(mode, protocol)

            # Start core tasks
            await self._start_core_tasks()

            # Start the display interface
            if mode == "gui":
                await self._start_gui_display()
            else:
                await self._start_cli_display()

            logger.info("Application started, press Ctrl+C to exit")

            # Wait for the application to run
            while self.running:
                await asyncio.sleep(1)

            return 0

        except Exception as e:
            logger.error(f"Failed to start application: {e}", exc_info=True)
            await self.shutdown()
            return 1
        finally:
            # Ensure the application is properly shut down
            try:
                await self.shutdown()
            except Exception as e:
                logger.error(f"Error during application shutdown: {e}")

    async def _initialize_components(self, mode: str, protocol: str):
        """
        Initialize application components.
        """
        logger.info("Initializing application components...")

        # Set display type (must be done before setting device state)
        self._set_display_type(mode)

        # Initialize MCP server
        self._initialize_mcp_server()

        # Set device state
        await self._set_device_state(DeviceState.IDLE)

        # Initialize IoT devices
        await self._initialize_iot_devices()

        # Initialize audio codec
        await self._initialize_audio()

        # Set protocol
        self._set_protocol_type(protocol)

        # Initialize wake word detector
        await self._initialize_wake_word_detector()

        # Set protocol callbacks
        self._setup_protocol_callbacks()

        # Start calendar reminder service
        await self._start_calendar_reminder_service()

        # Start timer service
        await self._start_timer_service()

        # Initialize shortcut manager
        await self._initialize_shortcuts()

        logger.info("Application components initialization complete")

    async def _initialize_audio(self):
        """
        Initialize audio devices and codecs.
        """
        try:
            logger.debug("Starting to initialize audio codec")
            from src.audio_codecs.audio_codec import AudioCodec

            self.audio_codec = AudioCodec()
            await self.audio_codec.initialize()

            # Set real-time encoding callback
            self.audio_codec.set_encoded_audio_callback(self._on_encoded_audio)

            logger.info("Audio codec initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize audio device: %s", e, exc_info=True)
            # Ensure audio_codec is None on initialization failure
            self.audio_codec = None

    def _on_encoded_audio(self, encoded_data: bytes):
        """
        Callback for handling encoded audio data.
        
        Note: This callback is called in the audio driver thread and needs to be thread-safely scheduled to the main event loop.
        """
        try:
            # Only send data when in listening state and audio channel is open
            if (self.device_state == DeviceState.LISTENING 
                    and self.protocol 
                    and self.protocol.is_audio_channel_opened()
                    and not getattr(self, '_transitioning', False)):
                
                # Thread-safely schedule to the main event loop
                if self._main_loop and not self._main_loop.is_closed():
                    self._main_loop.call_soon_threadsafe(
                        self._schedule_audio_send, encoded_data
                    )
                
        except Exception as e:
            logger.error(f"Failed to handle encoded audio data callback: {e}")

    def _schedule_audio_send(self, encoded_data: bytes):
        """
        Schedule audio sending task in the main event loop.
        """
        try:
            # Check the state again (it might have changed during scheduling)
            if (self.device_state == DeviceState.LISTENING 
                    and self.protocol 
                    and self.protocol.is_audio_channel_opened()):
                
                # Create an asynchronous task to send audio data
                asyncio.create_task(self.protocol.send_audio(encoded_data))
                
        except Exception as e:
            logger.error(f"Failed to schedule audio sending: {e}")

    def _set_protocol_type(self, protocol_type: str):
        """
        Set the protocol type.
        """
        logger.debug("Setting protocol type: %s", protocol_type)
        if protocol_type == "mqtt":
            self.protocol = MqttProtocol(asyncio.get_running_loop())
        else:
            self.protocol = WebsocketProtocol()

    def _set_display_type(self, mode: str):
        """
        Set the display interface type.
        """
        logger.debug("Setting display interface type: %s", mode)

        if mode == "gui":
            self.display = gui_display.GuiDisplay()
            self._setup_gui_callbacks()
        else:
            from src.display.cli_display import CliDisplay

            self.display = CliDisplay()
            self._setup_cli_callbacks()

    def _create_async_callback(self, coro_func, *args):
        """
        Helper method to create an asynchronous callback function.
        """
        return lambda: asyncio.create_task(coro_func(*args))

    def _setup_gui_callbacks(self):
        """
        Set up GUI callbacks.
        """
        asyncio.create_task(
            self.display.set_callbacks(
                press_callback=self._create_async_callback(self.start_listening),
                release_callback=self._create_async_callback(self.stop_listening),
                mode_callback=self._on_mode_changed,
                auto_callback=self._create_async_callback(self.toggle_chat_state),
                abort_callback=self._create_async_callback(
                    self.abort_speaking, AbortReason.WAKE_WORD_DETECTED
                ),
                send_text_callback=self._send_text_tts,
            )
        )

    def _setup_cli_callbacks(self):
        """
        Set up CLI callbacks.
        """
        asyncio.create_task(
            self.display.set_callbacks(
                auto_callback=self._create_async_callback(self.toggle_chat_state),
                abort_callback=self._create_async_callback(
                    self.abort_speaking, AbortReason.WAKE_WORD_DETECTED
                ),
                send_text_callback=self._send_text_tts,
            )
        )

    def _setup_protocol_callbacks(self):
        """
        Set up protocol callbacks.
        """
        self.protocol.on_network_error(self._on_network_error)
        self.protocol.on_incoming_audio(self._on_incoming_audio)
        self.protocol.on_incoming_json(self._on_incoming_json)
        self.protocol.on_audio_channel_opened(self._on_audio_channel_opened)
        self.protocol.on_audio_channel_closed(self._on_audio_channel_closed)

    async def _start_core_tasks(self):
        """
        Start core tasks.
        """
        logger.debug("Starting core tasks")

        # Command processing task
        self._create_task(self._command_processor(), "Command Processing")

    def _create_task(self, coro, name: str) -> asyncio.Task:
        """
        Create and manage a task.
        """
        task = asyncio.create_task(coro, name=name)
        self._main_tasks.add(task)

        def done_callback(t):
            # Remove the task from the set when it's done to prevent memory leaks
            self._main_tasks.discard(t)
            
            if not t.cancelled() and t.exception():
                logger.error(f"Task {name} ended with an exception: {t.exception()}", exc_info=True)

        task.add_done_callback(done_callback)
        return task

    async def _command_processor(self):
        """
        Command processor.
        """
        while self.running:
            try:
                # Check if the queue is initialized
                if self.command_queue is None:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Wait for a command, with a timeout to continue checking the running state
                try:
                    command = await asyncio.wait_for(
                        self.command_queue.get(), timeout=0.1
                    )
                    # Check if the command is valid
                    if command is None:
                        logger.warning("Received a null command, skipping execution")
                        continue
                    if not callable(command):
                        logger.warning(f"Received a non-callable command: {type(command)}, skipping execution")
                        continue

                    # Execute the command
                    result = command()
                    if asyncio.iscoroutine(result):
                        await result
                except asyncio.TimeoutError:
                    continue

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Command processing error: {e}", exc_info=True)

    async def _start_gui_display(self):
        """
        Start the GUI display.
        """
        # In a qasync environment, the GUI can be started directly in the main thread
        try:
            await self.display.start()
        except Exception as e:
            logger.error(f"GUI display error: {e}", exc_info=True)

    async def _start_cli_display(self):
        """
        Start the CLI display.
        """
        self._create_task(self.display.start(), "CLI Display")

    async def schedule_command(self, command):
        """
        Schedule a command to the command queue.
        """
        # Check if the queue is initialized
        if self.command_queue is None:
            logger.warning("Command queue not initialized, discarding command")
            return
            
        try:
            # Use put_nowait to avoid blocking, log a warning if the queue is full
            self.command_queue.put_nowait(command)
        except asyncio.QueueFull:
            logger.warning("Command queue is full, discarding command")
            # Optional: clear some old commands
            try:
                self.command_queue.get_nowait()
                self.command_queue.put_nowait(command)
                logger.info("Re-added after clearing an old command")
            except asyncio.QueueEmpty:
                pass

    async def _start_listening_common(self, listening_mode, keep_listening_flag):
        """
        Common logic for starting to listen.
        """
        async with self._state_lock:
            if self.device_state != DeviceState.IDLE:
                return False

        if not self.protocol.is_audio_channel_opened():
            success = await self.protocol.open_audio_channel()
            if not success:
                return False

        if self.audio_codec:
            await self.audio_codec.clear_audio_queue()

        await self._set_device_state(DeviceState.CONNECTING)

        self.keep_listening = keep_listening_flag
        await self.protocol.send_start_listening(listening_mode)
        await self._set_device_state(DeviceState.LISTENING)
        return True

    async def start_listening(self):
        """
        Start listening.
        """
        await self.schedule_command(self._start_listening_impl)

    async def _start_listening_impl(self):
        """
        Implementation for starting to listen.
        """
        success = await self._start_listening_common(ListeningMode.MANUAL, False)

        if not success and self.device_state == DeviceState.SPEAKING:
            if not self.aborted:
                await self.abort_speaking(AbortReason.WAKE_WORD_DETECTED)

    async def stop_listening(self):
        """
        Stop listening.
        """
        await self.schedule_command(self._stop_listening_impl)

    async def _stop_listening_impl(self):
        """
        Implementation for stopping listening.
        """
        if self.device_state == DeviceState.LISTENING:
            await self.protocol.send_stop_listening()
            await self._set_device_state(DeviceState.IDLE)

    async def toggle_chat_state(self):
        """
        Toggle the chat state.
        """
        await self.schedule_command(self._toggle_chat_state_impl)

    async def _toggle_chat_state_impl(self):
        """
        Implementation for toggling the chat state.
        """
        if self.device_state == DeviceState.IDLE:
            await self._start_listening_common(ListeningMode.AUTO_STOP, True)

        elif self.device_state == DeviceState.SPEAKING:
            await self.abort_speaking(AbortReason.NONE)
        elif self.device_state == DeviceState.LISTENING:
            await self.protocol.close_audio_channel()
            await self._set_device_state(DeviceState.IDLE)

    async def abort_speaking(self, reason):
        """
        Abort speech output.
        """
        if self.aborted:
            logger.debug(f"Already aborted, ignoring duplicate abort request: {reason}")
            return

        logger.info(f"Aborting speech output, reason: {reason}")
        self.aborted = True
        if self.audio_codec:
            await self.audio_codec.clear_audio_queue()

        try:
            await self.protocol.send_abort_speaking(reason)
            await self._set_device_state(DeviceState.IDLE)
            self.aborted = False
            if (
                reason == AbortReason.WAKE_WORD_DETECTED
                and self.keep_listening
                and self.protocol.is_audio_channel_opened()
            ):
                await asyncio.sleep(0.1)
                await self.toggle_chat_state()

        except Exception as e:
            logger.error(f"Error while aborting speech: {e}")

    async def _set_device_state(self, state):
        """
        Set the device state - ensure sequential execution via the queue.
        """
        await self.schedule_command(lambda: self._set_device_state_impl(state))

    def _update_display_async(self, update_func, *args):
        """
        Helper method for asynchronously updating the display.
        """
        if self.display:
            asyncio.create_task(update_func(*args))

    async def _set_device_state_impl(self, state):
        """
        Device state setting.
        """
        async with self._state_lock:
            if self.device_state == state:
                return

            logger.debug(f"Device state changed: {self.device_state} -> {state}")
            self.device_state = state

            # Perform corresponding actions and update the display based on the state
            if state == DeviceState.IDLE:
                await self._handle_idle_state()
            elif state == DeviceState.CONNECTING:
                self._update_display_async(self.display.update_status, "Connecting...")
            elif state == DeviceState.LISTENING:
                await self._handle_listening_state()
            elif state == DeviceState.SPEAKING:
                self._update_display_async(self.display.update_status, "Speaking...")

    async def _handle_idle_state(self):
        """
        Handle the idle state.
        """
        # Asynchronously execute UI updates
        self._update_display_async(self.display.update_status, "Standby")

        # Set emotion
        self.set_emotion("neutral")

    async def _handle_listening_state(self):
        """
        Handle the listening state.
        """
        # Asynchronously execute UI updates
        self._update_display_async(self.display.update_status, "Listening...")

        # Set emotion
        self.set_emotion("neutral")

        # Update IoT states
        await self._update_iot_states(True)

    async def _send_text_tts(self, text):
        """
        Send text for TTS.
        """
        if not self.protocol.is_audio_channel_opened():
            await self.protocol.open_audio_channel()

        await self.protocol.send_wake_word_detected(text)

    def set_chat_message(self, role, message):
        """
        Set a chat message.
        """
        self._update_display_async(self.display.update_text, message)

    def set_emotion(self, emotion):
        """
        Set an emotion.
        """
        self._update_display_async(self.display.update_emotion, emotion)

    # Protocol callback methods
    def _on_network_error(self, error_message=None):
        """
        Network error callback.
        """
        if error_message:
            logger.error(error_message)

        asyncio.create_task(self.schedule_command(self._handle_network_error))

    async def _handle_network_error(self):
        """
        Handle a network error.
        """
        self.keep_listening = False
        await self._set_device_state(DeviceState.IDLE)

        if self.protocol:
            await self.protocol.close_audio_channel()

    def _on_incoming_audio(self, data):
        """
        Callback for receiving audio data.
        """
        if self.device_state == DeviceState.SPEAKING and self.audio_codec:
            try:
                # Audio data processing requires real-time performance, so create a task directly but add exception handling
                task = asyncio.create_task(self.audio_codec.write_audio(data))
                task.add_done_callback(
                    lambda t: (
                        logger.error(
                            f"Audio writing task exception: {t.exception()}", exc_info=True
                        )
                        if not t.cancelled() and t.exception()
                        else None
                    )
                )
            except RuntimeError as e:
                logger.error(f"Unable to create audio writing task: {e}")
            except Exception as e:
                logger.error(f"Failed to create audio writing task: {e}", exc_info=True)

    def _on_incoming_json(self, json_data):
        """
        Callback for receiving JSON data.
        """
        asyncio.create_task(
            self.schedule_command(lambda: self._handle_incoming_json(json_data))
        )

    async def _handle_incoming_json(self, json_data):
        """
        Handle a JSON message.
        """
        try:
            if not json_data:
                return

            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            msg_type = data.get("type", "")

            handler = self._message_handlers.get(msg_type)
            if handler:
                await handler(data)
            else:
                logger.warning(f"Received a message of unknown type: {msg_type}")

        except Exception as e:
            logger.error(f"Error while handling JSON message: {e}", exc_info=True)

    async def _handle_tts_message(self, data):
        """
        Handle a TTS message.
        """
        state = data.get("state", "")
        if state == "start":
            await self._handle_tts_start()
        elif state == "stop":
            await self._handle_tts_stop()
        elif state == "sentence_start":
            text = data.get("text", "")
            if text:
                logger.info(f"<< {text}")
                self.set_chat_message("assistant", text)

                import re

                match = re.search(r"((?:\d\s*){6,})", text)
                if match:
                    await asyncio.to_thread(handle_verification_code, text)

    async def _handle_tts_start(self):
        """
        Handle the TTS start event.
        """
        logger.info(f"TTS started, current state: {self.device_state}")

        async with self._abort_lock:
            self.aborted = False

        if self.device_state in [DeviceState.IDLE, DeviceState.LISTENING]:
            await self._set_device_state(DeviceState.SPEAKING)

    async def _handle_tts_stop(self):
        """
        Handle the TTS stop event.
        """
        if self.device_state == DeviceState.SPEAKING:
            # Wait for audio playback to complete (improvement: add wait time and remove premature clearing)
            if self.audio_codec:
                logger.debug("Waiting for TTS audio playback to complete...")
                await self.audio_codec.wait_for_audio_complete()
                logger.debug("TTS audio playback complete")

            # Only wait for a short period for the buffer to stabilize if not interrupted
            if not self.aborted:
                await asyncio.sleep(0.2)  # Extra 200ms to ensure the tail end of the audio is played completely

            # State transition
            if self.keep_listening:
                await self.protocol.send_start_listening(ListeningMode.AUTO_STOP)
                await self._set_device_state(DeviceState.LISTENING)
            else:
                await self._set_device_state(DeviceState.IDLE)

    async def _handle_stt_message(self, data):
        """
        Handle an STT message.
        """
        text = data.get("text", "")
        if text:
            logger.info(f">> {text}")
            self.set_chat_message("user", text)

    async def _handle_llm_message(self, data):
        """
        Handle an LLM message.
        """
        emotion = data.get("emotion", "")
        if emotion:
            self.set_emotion(emotion)

    async def _on_audio_channel_opened(self):
        """
        Audio channel opened callback.
        """
        logger.info("Audio channel has been opened")

        if self.audio_codec:
            await self.audio_codec.start_streams()

        # Send IoT device descriptors
        from src.iot.thing_manager import ThingManager

        thing_manager = ThingManager.get_instance()
        descriptors_json = await thing_manager.get_descriptors_json()
        await self.protocol.send_iot_descriptors(descriptors_json)
        await self._update_iot_states(False)

    async def _on_audio_channel_closed(self):
        """
        Audio channel closed callback.
        """
        logger.info("Audio channel has been closed")
        await self._set_device_state(DeviceState.IDLE)
        self.keep_listening = False

    async def _initialize_wake_word_detector(self):
        """
        Initialize the wake word detector.
        """
        try:
            from src.audio_processing.wake_word_detect import WakeWordDetector

            self.wake_word_detector = WakeWordDetector()

            # Set callbacks
            self.wake_word_detector.on_detected(self._on_wake_word_detected)
            self.wake_word_detector.on_error = self._handle_wake_word_error

            await self.wake_word_detector.start(self.audio_codec)

            logger.info("Wake word detector initialized successfully")

        except RuntimeError as e:
            logger.info(f"Skipping wake word detector initialization: {e}")
            self.wake_word_detector = None
        except Exception as e:
            logger.error(f"Failed to initialize wake word detector: {e}")
            self.wake_word_detector = None

    async def _on_wake_word_detected(self, wake_word, full_text):
        """
        Wake word detected callback.
        """
        logger.info(f"Wake word detected: {wake_word}")

        if self.device_state == DeviceState.IDLE:
            await self._set_device_state(DeviceState.CONNECTING)
            await self._connect_and_start_listening(wake_word)
        elif self.device_state == DeviceState.SPEAKING:
            await self.abort_speaking(AbortReason.WAKE_WORD_DETECTED)

    async def _connect_and_start_listening(self, wake_word):
        """
        Connect to the server and start listening.
        """
        try:
            if not await self.protocol.connect():
                logger.error("Failed to connect to the server")
                await self._set_device_state(DeviceState.IDLE)
                return

            if not await self.protocol.open_audio_channel():
                logger.error("Failed to open audio channel")
                await self._set_device_state(DeviceState.IDLE)
                return

            await self.protocol.send_wake_word_detected("wake")
            self.keep_listening = True
            await self.protocol.send_start_listening(ListeningMode.AUTO_STOP)
            await self._set_device_state(DeviceState.LISTENING)

        except Exception as e:
            logger.error(f"Failed to connect and start listening: {e}")
            await self._set_device_state(DeviceState.IDLE)

    def _handle_wake_word_error(self, error):
        """
        Handle wake word detector errors.
        """
        logger.error(f"Wake word detection error: {error}")

    async def _initialize_iot_devices(self):
        """
        Initialize IoT devices.
        """
        from src.iot.thing_manager import ThingManager

        thing_manager = ThingManager.get_instance()

        await thing_manager.initialize_iot_devices(self.config)
        logger.info("IoT devices initialized successfully")

    async def _handle_iot_message(self, data):
        """
        Handle an IoT message.
        """
        from src.iot.thing_manager import ThingManager

        thing_manager = ThingManager.get_instance()
        commands = data.get("commands", [])
        print(f"IoT message: {commands}")
        for command in commands:
            try:
                result = await thing_manager.invoke(command)
                logger.info(f"Result of executing IoT command: {result}")
            except Exception as e:
                logger.error(f"Failed to execute IoT command: {e}")

    async def _update_iot_states(self, delta=None):
        """
        Update IoT device states.
        """
        from src.iot.thing_manager import ThingManager

        thing_manager = ThingManager.get_instance()

        try:
            if delta is None:
                # Directly use the asynchronous method to get the state
                states_json = await thing_manager.get_states_json_str()
                await self.protocol.send_iot_states(states_json)
            else:
                # Directly use the asynchronous method to get state changes
                changed, states_json = await thing_manager.get_states_json(delta=delta)
                if not delta or changed:
                    await self.protocol.send_iot_states(states_json)
        except Exception as e:
            logger.error(f"Failed to update IoT states: {e}")

    def _on_mode_changed(self):
        """
        Handle chat mode changes.
        """
        # Note: This is a synchronous method used in a GUI callback
        # A temporary task needs to be created to perform asynchronous lock operations
        try:
            # Quickly check the current state to avoid complex asynchronous operations in the GUI thread
            if self.device_state != DeviceState.IDLE:
                return False

            self.keep_listening = not self.keep_listening
            return True
        except Exception as e:
            logger.error(f"Mode change check failed: {e}")
            return False

    async def _safe_close_resource(
        self, resource, resource_name: str, close_method: str = "close"
    ):
        """
        Helper method to safely close a resource.
        """
        if resource:
            try:
                close_func = getattr(resource, close_method, None)
                if close_func:
                    if asyncio.iscoroutinefunction(close_func):
                        await close_func()
                    else:
                        close_func()
                logger.info(f"{resource_name} has been closed")
            except Exception as e:
                logger.error(f"Failed to close {resource_name}: {e}")

    async def shutdown(self):
        """
        Shut down the application.
        """
        if not self.running:
            return

        logger.info("Shutting down the application...")
        self.running = False

        # Set the shutdown event
        if self._shutdown_event is not None:
            self._shutdown_event.set()

        try:
            # 2. Close the wake word detector
            await self._safe_close_resource(
                self.wake_word_detector, "Wake Word Detector", "stop"
            )

            # 3. Cancel all long-running tasks
            if self._main_tasks:
                logger.info(f"Cancelling {len(self._main_tasks)} main tasks")
                tasks = list(self._main_tasks)
                for task in tasks:
                    if not task.done():
                        task.cancel()

                try:
                    # Wait for tasks to complete cancellation
                    await asyncio.wait(tasks, timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("Some tasks timed out during cancellation")
                except Exception as e:
                    logger.warning(f"Error while waiting for tasks to complete: {e}")

                self._main_tasks.clear()

            # 4. Close the protocol connection
            if self.protocol:
                try:
                    await self.protocol.close_audio_channel()
                    logger.info("Protocol connection has been closed")
                except Exception as e:
                    logger.error(f"Failed to close protocol connection: {e}")

            # 5. Close the audio device
            await self._safe_close_resource(self.audio_codec, "Audio Device")

            # 6. Close the MCP server
            await self._safe_close_resource(self.mcp_server, "MCP Server")

            # 7. Clear the queues
            try:
                for q in [
                    self.command_queue,
                ]:
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                logger.info("Queues have been cleared")
            except Exception as e:
                logger.error(f"Failed to clear queues: {e}")

            # 8. Finally, stop the UI display
            await self._safe_close_resource(self.display, "Display Interface")

            logger.info("Application shutdown complete")

        except Exception as e:
            logger.error(f"Error during application shutdown: {e}", exc_info=True)

    def _initialize_mcp_server(self):
        """
        Initialize the MCP server.
        """
        logger.info("Initializing MCP server")
        # Set the send callback
        self.mcp_server.set_send_callback(
            lambda msg: self.protocol.send_mcp_message(msg)
        )
        # Add common tools
        self.mcp_server.add_common_tools()

    async def _handle_mcp_message(self, data):
        """
        Handle an MCP message.
        """
        payload = data.get("payload")
        if payload:
            await self.mcp_server.parse_message(payload)

    async def _start_calendar_reminder_service(self):
        """
        Start the calendar reminder service.
        """
        try:
            logger.info("Starting calendar reminder service")
            from src.mcp.tools.calendar import get_reminder_service

            # Get the reminder service instance (via singleton pattern)
            reminder_service = get_reminder_service()

            # Start the reminder service (the service will handle initialization and schedule checking internally)
            await reminder_service.start()

            logger.info("Calendar reminder service has been started")

        except Exception as e:
            logger.error(f"Failed to start calendar reminder service: {e}", exc_info=True)

    async def _start_timer_service(self):
        """
        Start the timer service.
        """
        try:
            logger.info("Starting timer service")
            from src.mcp.tools.timer.timer_service import get_timer_service

            # Get the timer service instance (via singleton pattern)
            get_timer_service()

            logger.info("Timer service has been started and registered with the resource manager")

        except Exception as e:
            logger.error(f"Failed to start timer service: {e}", exc_info=True)

    async def _initialize_shortcuts(self):
        """
        Initialize the shortcut manager.
        """
        try:
            from src.views.components.shortcut_manager import (
                start_global_shortcuts_async,
            )

            shortcut_manager = await start_global_shortcuts_async(logger)
            if shortcut_manager:
                logger.info("Shortcut manager initialized successfully")
            else:
                logger.warning("Shortcut manager initialization failed")
        except Exception as e:
            logger.error(f"Failed to initialize shortcut manager: {e}", exc_info=True)