"""WebRTC Audio Processing Module.

This module provides audio processing functions from the WebRTC APM library,
such as Echo Cancellation (AEC) and Noise Suppression (NS).
It is extracted and optimized from webrtc_aec_demo.py for real-time processing.

Main features:
1. Echo Cancellation (AEC) - Eliminates interference from speaker output to microphone input.
2. Noise Suppression (NS) - Reduces ambient noise.
3. Automatic Gain Control (AGC) - Automatically adjusts audio gain.
4. High-pass Filtering - Removes low-frequency noise.

Usage:
    processor = WebRTCProcessor()
    processed_audio = processor.process_capture_stream(input_audio, reference_audio)
"""

import ctypes
import os
import threading
from ctypes import POINTER, Structure, byref, c_bool, c_float, c_int, c_short, c_void_p

import numpy as np

from src.utils.logging_config import get_logger
from src.utils.path_resolver import find_resource

logger = get_logger(__name__)


# Get the absolute path of the DLL file
def get_webrtc_dll_path():
    """
    Get the path to the WebRTC APM library.
    """
    dll_path = find_resource("libs/webrtc_apm/win/x86_64/libwebrtc_apm.dll")
    if dll_path:
        return str(dll_path)

    # Fallback solution: use the original logic
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    fallback_path = os.path.join(
        project_root, "libs", "webrtc_apm", "win", "x86_64", "libwebrtc_apm.dll"
    )
    logger.warning(f"WebRTC library not found, using fallback path: {fallback_path}")
    return fallback_path


# Load the WebRTC APM library
try:
    dll_path = get_webrtc_dll_path()
    apm_lib = ctypes.CDLL(dll_path)
    logger.info(f"Successfully loaded WebRTC APM library: {dll_path}")
except Exception as e:
    logger.error(f"Failed to load WebRTC APM library: {e}")
    apm_lib = None


# Define enumeration types
class DownmixMethod(ctypes.c_int):
    AverageChannels = 0
    UseFirstChannel = 1


class NoiseSuppressionLevel(ctypes.c_int):
    Low = 0
    Moderate = 1
    High = 2
    VeryHigh = 3


class GainControllerMode(ctypes.c_int):
    AdaptiveAnalog = 0
    AdaptiveDigital = 1
    FixedDigital = 2


class ClippingPredictorMode(ctypes.c_int):
    ClippingEventPrediction = 0
    AdaptiveStepClippingPeakPrediction = 1
    FixedStepClippingPeakPrediction = 2


# Define structures
class Pipeline(Structure):
    _fields_ = [
        ("MaximumInternalProcessingRate", c_int),
        ("MultiChannelRender", c_bool),
        ("MultiChannelCapture", c_bool),
        ("CaptureDownmixMethod", c_int),
    ]


class PreAmplifier(Structure):
    _fields_ = [("Enabled", c_bool), ("FixedGainFactor", c_float)]


class AnalogMicGainEmulation(Structure):
    _fields_ = [("Enabled", c_bool), ("InitialLevel", c_int)]


class CaptureLevelAdjustment(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("PreGainFactor", c_float),
        ("PostGainFactor", c_float),
        ("MicGainEmulation", AnalogMicGainEmulation),
    ]


class HighPassFilter(Structure):
    _fields_ = [("Enabled", c_bool), ("ApplyInFullBand", c_bool)]


class EchoCanceller(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("MobileMode", c_bool),
        ("ExportLinearAecOutput", c_bool),
        ("EnforceHighPassFiltering", c_bool),
    ]


class NoiseSuppression(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("NoiseLevel", c_int),
        ("AnalyzeLinearAecOutputWhenAvailable", c_bool),
    ]


class TransientSuppression(Structure):
    _fields_ = [("Enabled", c_bool)]


class ClippingPredictor(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("PredictorMode", c_int),
        ("WindowLength", c_int),
        ("ReferenceWindowLength", c_int),
        ("ReferenceWindowDelay", c_int),
        ("ClippingThreshold", c_float),
        ("CrestFactorMargin", c_float),
        ("UsePredictedStep", c_bool),
    ]


class AnalogGainController(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("StartupMinVolume", c_int),
        ("ClippedLevelMin", c_int),
        ("EnableDigitalAdaptive", c_bool),
        ("ClippedLevelStep", c_int),
        ("ClippedRatioThreshold", c_float),
        ("ClippedWaitFrames", c_int),
        ("Predictor", ClippingPredictor),
    ]


class GainController1(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("ControllerMode", c_int),
        ("TargetLevelDbfs", c_int),
        ("CompressionGainDb", c_int),
        ("EnableLimiter", c_bool),
        ("AnalogController", AnalogGainController),
    ]


class InputVolumeController(Structure):
    _fields_ = [("Enabled", c_bool)]


class AdaptiveDigital(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("HeadroomDb", c_float),
        ("MaxGainDb", c_float),
        ("InitialGainDb", c_float),
        ("MaxGainChangeDbPerSecond", c_float),
        ("MaxOutputNoiseLevelDbfs", c_float),
    ]


class FixedDigital(Structure):
    _fields_ = [("GainDb", c_float)]


class GainController2(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("VolumeController", InputVolumeController),
        ("AdaptiveController", AdaptiveDigital),
        ("FixedController", FixedDigital),
    ]


class Config(Structure):
    _fields_ = [
        ("PipelineConfig", Pipeline),
        ("PreAmp", PreAmplifier),
        ("LevelAdjustment", CaptureLevelAdjustment),
        ("HighPass", HighPassFilter),
        ("Echo", EchoCanceller),
        ("NoiseSuppress", NoiseSuppression),
        ("TransientSuppress", TransientSuppression),
        ("GainControl1", GainController1),
        ("GainControl2", GainController2),
    ]


# Define DLL function prototypes
if apm_lib:
    apm_lib.WebRTC_APM_Create.restype = c_void_p
    apm_lib.WebRTC_APM_Create.argtypes = []

    apm_lib.WebRTC_APM_Destroy.restype = None
    apm_lib.WebRTC_APM_Destroy.argtypes = [c_void_p]

    apm_lib.WebRTC_APM_CreateStreamConfig.restype = c_void_p
    apm_lib.WebRTC_APM_CreateStreamConfig.argtypes = [c_int, c_int]

    apm_lib.WebRTC_APM_DestroyStreamConfig.restype = None
    apm_lib.WebRTC_APM_DestroyStreamConfig.argtypes = [c_void_p]

    apm_lib.WebRTC_APM_ApplyConfig.restype = c_int
    apm_lib.WebRTC_APM_ApplyConfig.argtypes = [c_void_p, POINTER(Config)]

    apm_lib.WebRTC_APM_ProcessReverseStream.restype = c_int
    apm_lib.WebRTC_APM_ProcessReverseStream.argtypes = [
        c_void_p,
        POINTER(c_short),
        c_void_p,
        c_void_p,
        POINTER(c_short),
    ]

    apm_lib.WebRTC_APM_ProcessStream.restype = c_int
    apm_lib.WebRTC_APM_ProcessStream.argtypes = [
        c_void_p,
        POINTER(c_short),
        c_void_p,
        c_void_p,
        POINTER(c_short),
    ]

    apm_lib.WebRTC_APM_SetStreamDelayMs.restype = None
    apm_lib.WebRTC_APM_SetStreamDelayMs.argtypes = [c_void_p, c_int]


def create_optimized_apm_config():
    """
    Create an optimized WebRTC APM configuration, specifically for real-time audio processing.
    """
    config = Config()

    # Pipeline configuration - optimized for 16kHz
    config.PipelineConfig.MaximumInternalProcessingRate = 16000
    config.PipelineConfig.MultiChannelRender = False
    config.PipelineConfig.MultiChannelCapture = False
    config.PipelineConfig.CaptureDownmixMethod = DownmixMethod.AverageChannels

    # Pre-amplifier - disabled to reduce distortion
    config.PreAmp.Enabled = False
    config.PreAmp.FixedGainFactor = 1.0

    # Level adjustment - simplified configuration
    config.LevelAdjustment.Enabled = False
    config.LevelAdjustment.PreGainFactor = 1.0
    config.LevelAdjustment.PostGainFactor = 1.0
    config.LevelAdjustment.MicGainEmulation.Enabled = False
    config.LevelAdjustment.MicGainEmulation.InitialLevel = 100

    # High-pass filter - enabled to remove low-frequency noise
    config.HighPass.Enabled = True
    config.HighPass.ApplyInFullBand = True

    # Echo canceller - core feature
    config.Echo.Enabled = True
    config.Echo.MobileMode = False
    config.Echo.ExportLinearAecOutput = False
    config.Echo.EnforceHighPassFiltering = True

    # Noise suppression - moderate level
    config.NoiseSuppress.Enabled = True
    config.NoiseSuppress.NoiseLevel = NoiseSuppressionLevel.Moderate
    config.NoiseSuppress.AnalyzeLinearAecOutputWhenAvailable = True

    # Transient suppression - disabled to protect speech
    config.TransientSuppress.Enabled = False

    # Gain control 1 - enable adaptive digital gain
    config.GainControl1.Enabled = True
    config.GainControl1.ControllerMode = GainControllerMode.AdaptiveDigital
    config.GainControl1.TargetLevelDbfs = 3
    config.GainControl1.CompressionGainDb = 9
    config.GainControl1.EnableLimiter = True

    # Analog gain controller - disabled
    config.GainControl1.AnalogController.Enabled = False
    config.GainControl1.AnalogController.StartupMinVolume = 0
    config.GainControl1.AnalogController.ClippedLevelMin = 70
    config.GainControl1.AnalogController.EnableDigitalAdaptive = False
    config.GainControl1.AnalogController.ClippedLevelStep = 15
    config.GainControl1.AnalogController.ClippedRatioThreshold = 0.1
    config.GainControl1.AnalogController.ClippedWaitFrames = 300

    # Clipping predictor - disabled
    predictor = config.GainControl1.AnalogController.Predictor
    predictor.Enabled = False
    predictor.PredictorMode = ClippingPredictorMode.ClippingEventPrediction
    predictor.WindowLength = 5
    predictor.ReferenceWindowLength = 5
    predictor.ReferenceWindowDelay = 5
    predictor.ClippingThreshold = -1.0
    predictor.CrestFactorMargin = 3.0
    predictor.UsePredictedStep = True

    # Gain control 2 - disabled to avoid conflicts
    config.GainControl2.Enabled = False
    config.GainControl2.VolumeController.Enabled = False
    config.GainControl2.AdaptiveController.Enabled = False
    config.GainControl2.AdaptiveController.HeadroomDb = 5.0
    config.GainControl2.AdaptiveController.MaxGainDb = 30.0
    config.GainControl2.AdaptiveController.InitialGainDb = 15.0
    config.GainControl2.AdaptiveController.MaxGainChangeDbPerSecond = 6.0
    config.GainControl2.AdaptiveController.MaxOutputNoiseLevelDbfs = -50.0
    config.GainControl2.FixedController.GainDb = 0.0

    return config


class WebRTCProcessor:
    """
    WebRTC audio processor, providing real-time echo cancellation and audio enhancement.
    """

    def __init__(self, sample_rate=16000, channels=1, frame_size=160):
        """Initializes the WebRTC processor.

        Args:
            sample_rate: The sample rate, default 16000Hz.
            channels: The number of channels, default 1 (mono).
            frame_size: The frame size, default 160 samples (10ms @ 16kHz).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size = frame_size

        # WebRTC APM instance
        self.apm = None
        self.stream_config = None
        self.config = None

        # Thread-safe lock
        self._lock = threading.Lock()

        # Initialization state
        self._initialized = False

        # Reference signal buffer (for echo cancellation)
        self._reference_buffer = []
        self._reference_lock = threading.Lock()

        # Initialize WebRTC APM
        self._initialize()

    def _initialize(self):
        """
        Initializes WebRTC APM.
        """
        if not apm_lib:
            logger.error("WebRTC APM library not loaded, cannot initialize processor.")
            return False

        try:
            with self._lock:
                # Create APM instance
                self.apm = apm_lib.WebRTC_APM_Create()
                if not self.apm:
                    logger.error("Failed to create WebRTC APM instance.")
                    return False

                # Create stream configuration
                self.stream_config = apm_lib.WebRTC_APM_CreateStreamConfig(
                    self.sample_rate, self.channels
                )
                if not self.stream_config:
                    logger.error("Failed to create WebRTC stream configuration.")
                    return False

                # Apply configuration
                self.config = create_optimized_apm_config()
                result = apm_lib.WebRTC_APM_ApplyConfig(self.apm, byref(self.config))
                if result != 0:
                    logger.warning(f"Failed to apply WebRTC configuration, error code: {result}")

                # Set delay
                apm_lib.WebRTC_APM_SetStreamDelayMs(self.apm, 50)

                self._initialized = True
                logger.info("WebRTC processor initialized successfully.")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize WebRTC processor: {e}")
            return False

    def process_capture_stream(self, input_data, reference_data=None):
        """Processes the capture stream (microphone input).

        Args:
            input_data: The input audio data (bytes).
            reference_data: The reference audio data (bytes, optional).

        Returns:
            The processed audio data (bytes), or the original data on failure.
        """
        if not self._initialized or not self.apm:
            logger.warning("WebRTC processor not initialized, returning original data.")
            return input_data

        try:
            with self._lock:
                # Convert input data to a numpy array
                input_array = np.frombuffer(input_data, dtype=np.int16)

                # Check data length
                if len(input_array) != self.frame_size:
                    logger.warning(
                        f"Input data length mismatch, expected {self.frame_size}, got {len(input_array)}"
                    )
                    return input_data

                # Create input pointer
                input_ptr = input_array.ctypes.data_as(POINTER(c_short))

                # Create output buffer
                output_array = np.zeros(self.frame_size, dtype=np.int16)
                output_ptr = output_array.ctypes.data_as(POINTER(c_short))

                # Process reference signal (if provided)
                if reference_data:
                    self._process_reference_stream(reference_data)

                # Process capture stream
                result = apm_lib.WebRTC_APM_ProcessStream(
                    self.apm,
                    input_ptr,
                    self.stream_config,
                    self.stream_config,
                    output_ptr,
                )

                if result != 0:
                    logger.debug(f"WebRTC processing warning, error code: {result}")
                    # Return processed data even if there's a warning

                return output_array.tobytes()

        except Exception as e:
            logger.error(f"Failed to process capture stream: {e}")
            return input_data

    def _process_reference_stream(self, reference_data):
        """Processes the reference stream (speaker output).

        Args:
            reference_data: The reference audio data (bytes).
        """
        try:
            # Convert reference data to a numpy array
            ref_array = np.frombuffer(reference_data, dtype=np.int16)

            # Check data length
            if len(ref_array) != self.frame_size:
                # If length doesn't match, adjust to the correct length
                if len(ref_array) > self.frame_size:
                    ref_array = ref_array[: self.frame_size]
                else:
                    # Pad with zeros
                    padded = np.zeros(self.frame_size, dtype=np.int16)
                    padded[: len(ref_array)] = ref_array
                    ref_array = padded

            # Create reference signal pointer
            ref_ptr = ref_array.ctypes.data_as(POINTER(c_short))

            # Create reference output buffer (required but not used)
            ref_output_array = np.zeros(self.frame_size, dtype=np.int16)
            ref_output_ptr = ref_output_array.ctypes.data_as(POINTER(c_short))

            # Process reference stream
            result = apm_lib.WebRTC_APM_ProcessReverseStream(
                self.apm,
                ref_ptr,
                self.stream_config,
                self.stream_config,
                ref_output_ptr,
            )

            if result != 0:
                logger.debug(f"Processing reference stream warning, error code: {result}")

        except Exception as e:
            logger.error(f"Failed to process reference stream: {e}")

    def add_reference_data(self, reference_data):
        """Adds reference data to the buffer.

        Args:
            reference_data: The reference audio data (bytes).
        """
        with self._reference_lock:
            self._reference_buffer.append(reference_data)
            # Keep the buffer size reasonable (about 1 second of data)
            max_buffer_size = self.sample_rate // self.frame_size
            if len(self._reference_buffer) > max_buffer_size:
                self._reference_buffer = self._reference_buffer[-max_buffer_size:]

    def get_reference_data(self):
        """Gets and removes the oldest reference data.

        Returns:
            The reference audio data (bytes), or None if the buffer is empty.
        """
        with self._reference_lock:
            if self._reference_buffer:
                return self._reference_buffer.pop(0)
            return None

    def close(self):
        """
        Closes the WebRTC processor and releases resources.
        """
        if not self._initialized:
            return

        try:
            with self._lock:
                # Clear reference buffer
                with self._reference_lock:
                    self._reference_buffer.clear()

                # Destroy stream configuration
                if self.stream_config:
                    apm_lib.WebRTC_APM_DestroyStreamConfig(self.stream_config)
                    self.stream_config = None

                # Destroy APM instance
                if self.apm:
                    apm_lib.WebRTC_APM_Destroy(self.apm)
                    self.apm = None

                self._initialized = False
                logger.info("WebRTC processor has been closed.")

        except Exception as e:
            logger.error(f"Failed to close WebRTC processor: {e}")

    def __del__(self):
        """
        Destructor to ensure resources are released.
        """
        self.close()
