"""WebRTC Acoustic Echo Cancellation (AEC) demo script.

This script demonstrates the echo cancellation functionality of the WebRTC APM library:
1. Plays a specified audio file (as the reference signal)
2. Simultaneously records microphone input (containing echo and ambient sound)
3. Applies WebRTC echo cancellation processing
4. Saves the original and processed recordings for comparison

Usage:
    python webrtc_aec_demo.py [audio_file_path]

Example:
    python webrtc_aec_demo.py sample.wav
"""

import ctypes
import os
import sys
import threading
import time
import wave
from ctypes import POINTER, Structure, byref, c_bool, c_float, c_int, c_short, c_void_p

import numpy as np
import pyaudio
import pygame
import soundfile as sf
from pygame import mixer

# Get the absolute path to the DLL file
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
dll_path = os.path.join(
    project_root, "libs", "webrtc_apm", "win", "x86_64", "libwebrtc_apm.dll"
)

# Load the DLL
try:
    apm_lib = ctypes.CDLL(dll_path)
    print(f"Successfully loaded WebRTC APM library: {dll_path}")
except Exception as e:
    print(f"Failed to load WebRTC APM library: {e}")
    sys.exit(1)


# Define structures and enum types
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


# Define Pipeline structure
class Pipeline(Structure):
    _fields_ = [
        ("MaximumInternalProcessingRate", c_int),
        ("MultiChannelRender", c_bool),
        ("MultiChannelCapture", c_bool),
        ("CaptureDownmixMethod", c_int),
    ]


# Define PreAmplifier structure
class PreAmplifier(Structure):
    _fields_ = [("Enabled", c_bool), ("FixedGainFactor", c_float)]


# Define AnalogMicGainEmulation structure
class AnalogMicGainEmulation(Structure):
    _fields_ = [("Enabled", c_bool), ("InitialLevel", c_int)]


# Define CaptureLevelAdjustment structure
class CaptureLevelAdjustment(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("PreGainFactor", c_float),
        ("PostGainFactor", c_float),
        ("MicGainEmulation", AnalogMicGainEmulation),
    ]


# Define HighPassFilter structure
class HighPassFilter(Structure):
    _fields_ = [("Enabled", c_bool), ("ApplyInFullBand", c_bool)]


# Define EchoCanceller structure
class EchoCanceller(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("MobileMode", c_bool),
        ("ExportLinearAecOutput", c_bool),
        ("EnforceHighPassFiltering", c_bool),
    ]


# Define NoiseSuppression structure
class NoiseSuppression(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("NoiseLevel", c_int),
        ("AnalyzeLinearAecOutputWhenAvailable", c_bool),
    ]


# Define TransientSuppression structure
class TransientSuppression(Structure):
    _fields_ = [("Enabled", c_bool)]


# Define ClippingPredictor structure
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


# Define AnalogGainController structure
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


# Define GainController1 structure
class GainController1(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("ControllerMode", c_int),
        ("TargetLevelDbfs", c_int),
        ("CompressionGainDb", c_int),
        ("EnableLimiter", c_bool),
        ("AnalogController", AnalogGainController),
    ]


# Define InputVolumeController structure
class InputVolumeController(Structure):
    _fields_ = [("Enabled", c_bool)]


# Define AdaptiveDigital structure
class AdaptiveDigital(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("HeadroomDb", c_float),
        ("MaxGainDb", c_float),
        ("InitialGainDb", c_float),
        ("MaxGainChangeDbPerSecond", c_float),
        ("MaxOutputNoiseLevelDbfs", c_float),
    ]


# Define FixedDigital structure
class FixedDigital(Structure):
    _fields_ = [("GainDb", c_float)]


# Define GainController2 structure
class GainController2(Structure):
    _fields_ = [
        ("Enabled", c_bool),
        ("VolumeController", InputVolumeController),
        ("AdaptiveController", AdaptiveDigital),
        ("FixedController", FixedDigital),
    ]


# Define the complete Config structure
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


def create_apm_config():
    """Create WebRTC APM configuration - optimized to preserve natural speech and reduce error code -11 issues."""
    config = Config()

    # Set Pipeline configuration - use standard sample rate to avoid resampling issues
    config.PipelineConfig.MaximumInternalProcessingRate = 16000  # WebRTC optimized frequency
    config.PipelineConfig.MultiChannelRender = False
    config.PipelineConfig.MultiChannelCapture = False
    config.PipelineConfig.CaptureDownmixMethod = DownmixMethod.AverageChannels

    # Set PreAmplifier configuration - reduce pre-amplification interference
    config.PreAmp.Enabled = False  # Disable pre-amplification to avoid distortion
    config.PreAmp.FixedGainFactor = 1.0  # No gain

    # Set LevelAdjustment configuration - simplify level adjustment
    config.LevelAdjustment.Enabled = False  # Disable level adjustment to reduce processing conflicts
    config.LevelAdjustment.PreGainFactor = 1.0
    config.LevelAdjustment.PostGainFactor = 1.0
    config.LevelAdjustment.MicGainEmulation.Enabled = False
    config.LevelAdjustment.MicGainEmulation.InitialLevel = 100  # Lower initial level to avoid oversaturation

    # Set HighPassFilter configuration - use standard high-pass filtering
    config.HighPass.Enabled = True  # Enable high-pass filter to remove low-frequency noise
    config.HighPass.ApplyInFullBand = True  # Apply across full band for better compatibility

    # Set EchoCanceller configuration - optimize echo cancellation
    config.Echo.Enabled = True  # Enable echo cancellation
    config.Echo.MobileMode = False  # Use standard mode instead of mobile mode for better results
    config.Echo.ExportLinearAecOutput = False
    config.Echo.EnforceHighPassFiltering = True  # Enable enforced high-pass filtering to help eliminate low-frequency echo

    # Set NoiseSuppression configuration - moderate noise suppression
    config.NoiseSuppress.Enabled = True
    config.NoiseSuppress.NoiseLevel = NoiseSuppressionLevel.Moderate  # Moderate level suppression
    config.NoiseSuppress.AnalyzeLinearAecOutputWhenAvailable = True

    # Set TransientSuppression configuration
    config.TransientSuppress.Enabled = False  # Disable transient suppression to avoid clipping speech

    # Set GainController1 configuration - light gain control
    config.GainControl1.Enabled = True  # Enable gain control
    config.GainControl1.ControllerMode = GainControllerMode.AdaptiveDigital
    config.GainControl1.TargetLevelDbfs = 3  # Lower target level (more aggressive control)
    config.GainControl1.CompressionGainDb = 9  # Moderate compression gain
    config.GainControl1.EnableLimiter = True  # Enable limiter

    # AnalogGainController
    config.GainControl1.AnalogController.Enabled = False  # Disable analog gain control
    config.GainControl1.AnalogController.StartupMinVolume = 0
    config.GainControl1.AnalogController.ClippedLevelMin = 70
    config.GainControl1.AnalogController.EnableDigitalAdaptive = False
    config.GainControl1.AnalogController.ClippedLevelStep = 15
    config.GainControl1.AnalogController.ClippedRatioThreshold = 0.1
    config.GainControl1.AnalogController.ClippedWaitFrames = 300

    # ClippingPredictor
    predictor = config.GainControl1.AnalogController.Predictor
    predictor.Enabled = False
    predictor.PredictorMode = ClippingPredictorMode.ClippingEventPrediction
    predictor.WindowLength = 5
    predictor.ReferenceWindowLength = 5
    predictor.ReferenceWindowDelay = 5
    predictor.ClippingThreshold = -1.0
    predictor.CrestFactorMargin = 3.0
    predictor.UsePredictedStep = True

    # Set GainController2 configuration - disabled to avoid conflicts
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


# Reference audio buffer (for storing speaker output)
reference_buffer = []
reference_lock = threading.Lock()


def record_playback_audio(chunk_size, sample_rate, channels):
    """
    Record audio from the speaker output (more accurate reference signal).
    """
    global reference_buffer

    # Note: This is the ideal implementation, but PyAudio on Windows typically cannot directly record speaker output.
    # In practice, other methods are needed to capture system audio output.
    try:
        p = pyaudio.PyAudio()

        # Try to create a stream that records from the default output device (supported on some systems)
        # Note: This does not work on most systems; it is included here only as an example
        loopback_stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk_size,
            input_device_index=None,  # Try to use the default output device as the input source
        )

        # Start recording
        while True:
            try:
                data = loopback_stream.read(chunk_size, exception_on_overflow=False)
                with reference_lock:
                    reference_buffer.append(data)
            except OSError:
                break

            # Keep buffer size reasonable
            with reference_lock:
                if len(reference_buffer) > 100:  # Keep approximately 2 seconds of buffer
                    reference_buffer = reference_buffer[-100:]
    except Exception as e:
        print(f"Unable to record system audio: {e}")
    finally:
        try:
            if "loopback_stream" in locals() and loopback_stream:
                loopback_stream.stop_stream()
                loopback_stream.close()
            if "p" in locals() and p:
                p.terminate()
        except Exception:
            pass


def aec_demo(audio_file):
    """
    WebRTC echo cancellation demo main function.
    """
    # Check if the audio file exists
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        return

    # Audio parameter settings - use WebRTC-optimized audio parameters
    SAMPLE_RATE = 16000  # 16kHz sample rate (WebRTC AEC optimized sample rate)
    CHANNELS = 1  # Mono
    CHUNK = 160  # Samples per frame (10ms @ 16kHz, WebRTC standard frame size)
    FORMAT = pyaudio.paInt16  # 16-bit PCM format

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # List all available audio devices for reference
    print("\nAvailable audio devices:")
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        print(f"Device {i}: {dev_info['name']}")
        print(f"  - Input channels: {dev_info['maxInputChannels']}")
        print(f"  - Output channels: {dev_info['maxOutputChannels']}")
        print(f"  - Default sample rate: {dev_info['defaultSampleRate']}")
    print("")

    # Open microphone input stream
    input_stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    # Initialize pygame for audio playback
    pygame.init()
    mixer.init(frequency=SAMPLE_RATE, size=-16, channels=CHANNELS, buffer=CHUNK * 4)

    # Load reference audio file
    print(f"Loading audio file: {audio_file}")

    # Read reference audio file and convert sample rate/channels
    # Note: soundfile library is used here to load audio files for multi-format support and resampling
    try:
        print("Loading reference audio...")
        # Read original audio using soundfile library
        ref_audio_data, orig_sr = sf.read(audio_file, dtype="int16")
        print(
            f"Original audio: sample_rate={orig_sr}, channels="
            f"{ref_audio_data.shape[1] if len(ref_audio_data.shape) > 1 else 1}"
        )

        # Convert to mono (if stereo)
        if len(ref_audio_data.shape) > 1 and ref_audio_data.shape[1] > 1:
            ref_audio_data = ref_audio_data.mean(axis=1).astype(np.int16)

        # Convert sample rate (if needed)
        if orig_sr != SAMPLE_RATE:
            print(f"Resampling reference audio from {orig_sr}Hz to {SAMPLE_RATE}Hz...")
            # Use librosa or scipy for resampling
            from scipy import signal

            ref_audio_data = signal.resample(
                ref_audio_data, int(len(ref_audio_data) * SAMPLE_RATE / orig_sr)
            ).astype(np.int16)

        # Save as temporary wav file for pygame playback
        temp_wav_path = os.path.join(current_dir, "temp_reference.wav")
        with wave.open(temp_wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes (16-bit)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(ref_audio_data.tobytes())

        # Split reference audio into CHUNK-sized frames
        ref_audio_frames = []
        for i in range(0, len(ref_audio_data), CHUNK):
            if i + CHUNK <= len(ref_audio_data):
                ref_audio_frames.append(ref_audio_data[i : i + CHUNK])
            else:
                # Last frame is smaller than CHUNK size, pad with zeros
                last_frame = np.zeros(CHUNK, dtype=np.int16)
                last_frame[: len(ref_audio_data) - i] = ref_audio_data[i:]
                ref_audio_frames.append(last_frame)

        print(f"Reference audio ready, total {len(ref_audio_frames)} frames")

        # Load the processed temporary WAV file
        mixer.music.load(temp_wav_path)
    except Exception as e:
        print(f"Error loading reference audio: {e}")
        sys.exit(1)

    # Create WebRTC APM instance
    apm = apm_lib.WebRTC_APM_Create()

    # Apply APM configuration
    config = create_apm_config()
    result = apm_lib.WebRTC_APM_ApplyConfig(apm, byref(config))
    if result != 0:
        print(f"Warning: APM configuration failed, error code: {result}")

    # Create stream configuration
    stream_config = apm_lib.WebRTC_APM_CreateStreamConfig(SAMPLE_RATE, CHANNELS)

    # Set a small delay to more accurately match the reference signal and microphone signal
    apm_lib.WebRTC_APM_SetStreamDelayMs(apm, 50)

    # Create recording buffers
    original_frames = []
    processed_frames = []
    reference_frames = []

    # 等待一会让音频系统准备好
    time.sleep(0.5)

    print("开始录制和处理...")
    print("播放参考音频...")

    mixer.music.play()

    # 录制持续时间(根据音频文件长度)
    try:
        sound_length = mixer.Sound(temp_wav_path).get_length()
        recording_time = sound_length if sound_length > 0 else 10
    except Exception:
        recording_time = 10  # 如果无法获取长度，默认10秒

    recording_time += 1  # 额外1秒确保捕获所有音频

    start_time = time.time()
    current_ref_frame_index = 0
    try:
        while time.time() - start_time < recording_time:
            # 从麦克风读取一帧数据
            input_data = input_stream.read(CHUNK, exception_on_overflow=False)

            # 保存原始录音
            original_frames.append(input_data)

            # 将输入数据转换为short数组
            input_array = np.frombuffer(input_data, dtype=np.int16)
            input_ptr = input_array.ctypes.data_as(POINTER(c_short))

            # 获取当前参考音频帧
            if current_ref_frame_index < len(ref_audio_frames):
                ref_array = ref_audio_frames[current_ref_frame_index]
                reference_frames.append(ref_array.tobytes())
                current_ref_frame_index += 1
            else:
                # 如果参考音频播放完毕，使用静音帧
                ref_array = np.zeros(CHUNK, dtype=np.int16)
                reference_frames.append(ref_array.tobytes())

            ref_ptr = ref_array.ctypes.data_as(POINTER(c_short))

            # 创建输出缓冲区
            output_array = np.zeros(CHUNK, dtype=np.int16)
            output_ptr = output_array.ctypes.data_as(POINTER(c_short))

            # 重要：先处理参考信号（扬声器输出）
            # 创建参考信号的输出缓冲区（虽然不使用但必须提供）
            ref_output_array = np.zeros(CHUNK, dtype=np.int16)
            ref_output_ptr = ref_output_array.ctypes.data_as(POINTER(c_short))

            result_reverse = apm_lib.WebRTC_APM_ProcessReverseStream(
                apm, ref_ptr, stream_config, stream_config, ref_output_ptr
            )

            if result_reverse != 0:
                print(f"\r警告: 参考信号处理失败，错误码: {result_reverse}")

            # 然后处理麦克风信号，应用回声消除
            result = apm_lib.WebRTC_APM_ProcessStream(
                apm, input_ptr, stream_config, stream_config, output_ptr
            )

            if result != 0:
                print(f"\r警告: 处理失败，错误码: {result}")

            # 保存处理后的音频帧
            processed_frames.append(output_array.tobytes())

            # 计算并显示进度
            progress = (time.time() - start_time) / recording_time * 100
            sys.stdout.write(f"\r处理进度: {progress:.1f}%")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n录制被用户中断")
    finally:
        print("\n录制和处理完成")

        # 停止播放
        mixer.music.stop()

        # 关闭音频流
        input_stream.stop_stream()
        input_stream.close()

        # 释放APM资源
        apm_lib.WebRTC_APM_DestroyStreamConfig(stream_config)
        apm_lib.WebRTC_APM_Destroy(apm)

        # 关闭PyAudio
        p.terminate()

        # 保存原始录音
        original_output_path = os.path.join(current_dir, "original_recording.wav")
        save_wav(original_output_path, original_frames, SAMPLE_RATE, CHANNELS)

        # 保存处理后的录音
        processed_output_path = os.path.join(current_dir, "processed_recording.wav")
        save_wav(processed_output_path, processed_frames, SAMPLE_RATE, CHANNELS)

        # 保存参考音频（播放的音频）
        reference_output_path = os.path.join(current_dir, "reference_playback.wav")
        save_wav(reference_output_path, reference_frames, SAMPLE_RATE, CHANNELS)

        # 删除临时文件
        if os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception:
                pass

        print(f"原始录音已保存至: {original_output_path}")
        print(f"处理后的录音已保存至: {processed_output_path}")
        print(f"参考音频已保存至: {reference_output_path}")

        # 退出pygame
        pygame.quit()


def save_wav(file_path, frames, sample_rate, channels):
    """
    将音频帧保存为WAV文件.
    """
    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 2字节(16位)
        wf.setframerate(sample_rate)
        if isinstance(frames[0], bytes):
            wf.writeframes(b"".join(frames))
        else:
            wf.writeframes(b"".join([f for f in frames if isinstance(f, bytes)]))


if __name__ == "__main__":
    # 获取命令行参数
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        # 默认使用scripts目录下的鞠婧祎.wav
        audio_file = os.path.join(current_dir, "鞠婧祎.wav")

        # 如果默认文件不存在，尝试MP3版本
        if not os.path.exists(audio_file):
            audio_file = os.path.join(current_dir, "鞠婧祎.mp3")
            if not os.path.exists(audio_file):
                print("错误: 找不到默认音频文件，请指定要播放的音频文件路径")
                print("用法: python webrtc_aec_demo.py [音频文件路径]")
                sys.exit(1)

    # 运行演示
    aec_demo(audio_file)
