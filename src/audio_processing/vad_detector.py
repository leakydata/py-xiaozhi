import logging
import threading
import time
from collections import deque

import numpy as np
import pyaudio
import webrtcvad

from src.constants.constants import AbortReason, DeviceState

logger = logging.getLogger("VADDetector")


class VADDetector:
    """
    Voice Activity Detector based on WebRTC VAD with adaptive energy thresholding.
    Detects when the user is speaking while the assistant is talking (barge-in).
    """

    def __init__(self, audio_codec, protocol, app_instance, loop):
        self.audio_codec = audio_codec
        self.protocol = protocol
        self.app = app_instance
        self.loop = loop

        # VAD settings
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(2)  # Mode 2: balanced between sensitivity and false positives

        # Audio parameters
        self.sample_rate = 16000
        self.frame_duration = 20  # milliseconds
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)

        # Adaptive energy threshold
        self._energy_history = deque(maxlen=200)  # ~4 seconds of ambient noise tracking
        self._energy_threshold = 300  # Initial threshold
        self._min_energy_threshold = 150
        self._energy_multiplier = 2.5  # Speech must be this many times louder than ambient

        # Detection parameters
        self.speech_window = 4  # Consecutive speech frames to trigger interruption
        self.silence_reset_window = 8  # Consecutive silence frames to reset speech count

        # State variables
        self.running = False
        self.paused = False
        self.thread = None
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

        # Independent audio stream
        self.pa = None
        self.stream = None

    def start(self):
        """Starts the VAD detector."""
        if self.thread and self.thread.is_alive():
            logger.warning("VAD detector is already running")
            return

        self.running = True
        self.paused = False
        self._initialize_audio_stream()

        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        logger.info("VAD detector started with adaptive thresholding")

    def stop(self):
        """Stops the VAD detector."""
        self.running = False
        self._close_audio_stream()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        logger.info("VAD detector stopped")

    def pause(self):
        """Pauses VAD detection."""
        self.paused = True

    def resume(self):
        """Resumes VAD detection."""
        self.paused = False
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

    def is_running(self):
        return self.running and not self.paused

    def _initialize_audio_stream(self):
        """Initializes an independent audio stream."""
        try:
            self.pa = pyaudio.PyAudio()

            device_index = None
            for i in range(self.pa.get_device_count()):
                device_info = self.pa.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    device_index = i
                    break

            if device_index is None:
                logger.error("No available input device found")
                return False

            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.frame_size,
                start=True,
            )

            logger.info(f"VAD audio stream initialized, device: {device_index}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize VAD audio stream: {e}")
            return False

    def _close_audio_stream(self):
        """Closes the audio stream."""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

            if self.pa:
                self.pa.terminate()
                self.pa = None

        except Exception as e:
            logger.error(f"Failed to close VAD audio stream: {e}")

    def _update_adaptive_threshold(self, energy: float, is_speech: bool):
        """Update the adaptive energy threshold based on ambient noise levels."""
        if not is_speech:
            # Only track ambient noise when no speech detected
            self._energy_history.append(energy)

        if len(self._energy_history) >= 20:
            # Set threshold as a multiple of the median ambient energy
            ambient_median = float(np.median(list(self._energy_history)))
            self._energy_threshold = max(
                self._min_energy_threshold,
                ambient_median * self._energy_multiplier,
            )

    def _detection_loop(self):
        """VAD detection main loop."""
        while self.running:
            if self.paused or not self.stream:
                time.sleep(0.1)
                continue

            try:
                if self.app.device_state == DeviceState.SPEAKING:
                    frame = self._read_audio_frame()
                    if not frame:
                        time.sleep(0.01)
                        continue

                    is_speech, energy = self._detect_speech(frame)
                    self._update_adaptive_threshold(energy, is_speech)

                    if is_speech:
                        self._handle_speech_frame()
                    else:
                        self._handle_silence_frame()
                else:
                    self._reset_state()

            except Exception as e:
                logger.error(f"Error in VAD detection loop: {e}")

            time.sleep(0.01)

    def _read_audio_frame(self):
        """Reads one frame of audio data."""
        try:
            if not self.stream or not self.stream.is_active():
                return None
            return self.stream.read(self.frame_size, exception_on_overflow=False)
        except Exception as e:
            logger.error(f"Failed to read audio frame: {e}")
            return None

    def _detect_speech(self, frame):
        """Detects speech using VAD + adaptive energy threshold. Returns (is_speech, energy)."""
        try:
            if len(frame) != self.frame_size * 2:
                return False, 0.0

            is_speech = self.vad.is_speech(frame, self.sample_rate)
            audio_data = np.frombuffer(frame, dtype=np.int16)
            energy = float(np.mean(np.abs(audio_data)))

            is_valid_speech = is_speech and energy > self._energy_threshold

            if is_valid_speech:
                logger.debug(
                    f"Speech detected [energy: {energy:.0f}, threshold: {self._energy_threshold:.0f}, "
                    f"consecutive: {self.speech_count + 1}]"
                )

            return is_valid_speech, energy
        except Exception as e:
            logger.error(f"Failed to detect speech: {e}")
            return False, 0.0

    def _handle_speech_frame(self):
        """Handles a speech frame."""
        self.speech_count += 1
        self.silence_count = 0

        if self.speech_count >= self.speech_window and not self.triggered:
            self.triggered = True
            logger.info(
                f"Barge-in detected! (consecutive frames: {self.speech_count}, "
                f"threshold: {self._energy_threshold:.0f})"
            )
            self._trigger_interrupt()
            self.paused = True
            self._reset_state()

    def _handle_silence_frame(self):
        """Handles a silence frame."""
        self.silence_count += 1
        if self.silence_count >= self.silence_reset_window:
            self.speech_count = 0

    def _reset_state(self):
        """Resets the state."""
        self.speech_count = 0
        self.silence_count = 0
        self.triggered = False

    def _trigger_interrupt(self):
        """Triggers an interruption."""
        self.app.schedule(
            lambda: self.app.abort_speaking(AbortReason.WAKE_WORD_DETECTED)
        )
