import logging
import threading
import time

import numpy as np
import pyaudio
import webrtcvad

from src.constants.constants import AbortReason, DeviceState

# Configure logging
logger = logging.getLogger("VADDetector")


class VADDetector:
    """
    Voice Activity Detector based on WebRTC VAD, used to detect user interruptions.
    """

    def __init__(self, audio_codec, protocol, app_instance, loop):
        """Initializes the VAD detector.

        Args:
            audio_codec: Audio codec instance
            protocol: Communication protocol instance
            app_instance: Application instance
            loop: Event loop
        """
        self.audio_codec = audio_codec
        self.protocol = protocol
        self.app = app_instance
        self.loop = loop

        # VAD settings
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(3)  # Set the highest sensitivity

        # Parameter settings
        self.sample_rate = 16000
        self.frame_duration = 20  # milliseconds
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        self.speech_window = 5  # How many consecutive frames of speech must be detected to trigger an interruption
        self.energy_threshold = 300  # Energy threshold

        # State variables
        self.running = False
        self.paused = False
        self.thread = None
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

        # Create an independent PyAudio instance and stream to avoid conflicts with the main audio stream
        self.pa = None
        self.stream = None

    def start(self):
        """
        Starts the VAD detector.
        """
        if self.thread and self.thread.is_alive():
            logger.warning("VAD detector is already running")
            return

        self.running = True
        self.paused = False

        # Initialize PyAudio and stream
        self._initialize_audio_stream()

        # Start detection thread
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        logger.info("VAD detector started")

    def stop(self):
        """
        Stops the VAD detector.
        """
        self.running = False

        # Close the audio stream
        self._close_audio_stream()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        logger.info("VAD detector stopped")

    def pause(self):
        """
        Pauses VAD detection.
        """
        self.paused = True
        logger.info("VAD detector paused")

    def resume(self):
        """
        Resumes VAD detection.
        """
        self.paused = False
        # Reset state
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False
        logger.info("VAD detector resumed")

    def is_running(self):
        """
        Checks if the VAD detector is running.
        """
        return self.running and not self.paused

    def _initialize_audio_stream(self):
        """
        Initializes an independent audio stream.
        """
        try:
            # Create PyAudio instance
            self.pa = pyaudio.PyAudio()

            # Get default input device
            device_index = None
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    device_index = i
                    break

            if device_index is None:
                logger.error("No available input device found")
                return False

            # Create input stream
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.frame_size,
                start=True,
            )

            logger.info(f"VAD detector audio stream initialized, using device index: {device_index}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize VAD audio stream: {e}")
            return False

    def _close_audio_stream(self):
        """
        Closes the audio stream.
        """
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

            if self.pa:
                self.pa.terminate()
                self.pa = None

            logger.info("VAD detector audio stream closed")
        except Exception as e:
            logger.error(f"Failed to close VAD audio stream: {e}")

    def _detection_loop(self):
        """
        VAD detection main loop.
        """
        logger.info("VAD detection loop started")

        while self.running:
            # If paused or the audio stream is not initialized, skip
            if self.paused or not self.stream:
                time.sleep(0.1)
                continue

            try:
                # Only perform detection in the speaking state
                if self.app.device_state == DeviceState.SPEAKING:
                    # Read audio frame
                    frame = self._read_audio_frame()
                    if not frame:
                        time.sleep(0.01)
                        continue

                    # Detect if it is speech
                    is_speech = self._detect_speech(frame)

                    # If speech is detected and the trigger condition is met, handle the interruption
                    if is_speech:
                        self._handle_speech_frame(frame)
                    else:
                        self._handle_silence_frame(frame)
                else:
                    # Not in speaking state, reset state
                    self._reset_state()

            except Exception as e:
                logger.error(f"Error in VAD detection loop: {e}")

            time.sleep(0.01)  # Small delay to reduce CPU usage

        logger.info("VAD detection loop ended")

    def _read_audio_frame(self):
        """
        Reads one frame of audio data.
        """
        try:
            if not self.stream or not self.stream.is_active():
                return None

            # Read audio data
            data = self.stream.read(self.frame_size, exception_on_overflow=False)
            return data
        except Exception as e:
            logger.error(f"Failed to read audio frame: {e}")
            return None

    def _detect_speech(self, frame):
        """
        Detects if it is speech.
        """
        try:
            # Ensure the frame length is correct
            if len(frame) != self.frame_size * 2:  # 16-bit audio, 2 bytes per sample
                return False

            # Use VAD for detection
            is_speech = self.vad.is_speech(frame, self.sample_rate)

            # Calculate audio energy
            audio_data = np.frombuffer(frame, dtype=np.int16)
            energy = np.mean(np.abs(audio_data))

            # Combine VAD and energy threshold
            is_valid_speech = is_speech and energy > self.energy_threshold

            if is_valid_speech:
                logger.debug(
                    f"Speech detected [Energy: {energy:.2f}] [Consecutive speech frames: {self.speech_count+1}]"
                )

            return is_valid_speech
        except Exception as e:
            logger.error(f"Failed to detect speech: {e}")
            return False

    def _handle_speech_frame(self, frame):
        """
        Handles a speech frame.
        """
        self.speech_count += 1
        self.silence_count = 0

        # Sufficient consecutive speech frames detected, triggering interruption
        if self.speech_count >= self.speech_window and not self.triggered:
            self.triggered = True
            logger.info("Continuous speech detected, triggering interruption!")
            self._trigger_interrupt()

            # Pause itself immediately to prevent repeated triggers
            self.paused = True
            logger.info("VAD detector has been automatically paused to prevent repeated triggers")

            # Reset state
            self.speech_count = 0
            self.silence_count = 0
            self.triggered = False

    def _handle_silence_frame(self, frame):
        """
        Handles a silence frame.
        """
        self.silence_count += 1
        self.speech_count = 0

    def _reset_state(self):
        """
        Resets the state.
        """
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

    def _trigger_interrupt(self):
        """
        Triggers an interruption.
        """
        # Notify the application to abort the current voice output
        self.app.schedule(
            lambda: self.app.abort_speaking(AbortReason.WAKE_WORD_DETECTED)
        )
