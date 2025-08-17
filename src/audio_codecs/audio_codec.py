import asyncio
import gc
import time
from collections import deque
from typing import Optional

import numpy as np
import opuslib
import sounddevice as sd
import soxr

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AudioCodec:
    """
    Audio codec, responsible for recording encoding and playback decoding
    """

    def __init__(self):
        self.opus_encoder = None
        self.opus_decoder = None

        # Device sample rate information
        self.device_input_sample_rate = None
        self.device_output_sample_rate = None

        # Input resampler
        self.input_resampler = None

        # Resample buffer, use deque to improve performance
        self._resample_input_buffer = deque()

        # Input frame size cache
        self._device_input_frame_size = None

        # Closing status flag
        self._is_closing = False

        # Audio stream objects
        self.input_stream = None
        self.output_stream = None

        # Audio data queues
        self._wakeword_buffer = asyncio.Queue(maxsize=100)  # Wake word detection
        self._output_buffer = asyncio.Queue(maxsize=500)  # Audio playback
        
        # Real-time encoding callback
        self._encoded_audio_callback = None

    async def initialize(self):
        """
        Initialize audio devices and codecs
        """
        try:
            # Query device sample rates
            input_device_info = sd.query_devices(sd.default.device[0])
            output_device_info = sd.query_devices(sd.default.device[1])

            self.device_input_sample_rate = int(input_device_info["default_samplerate"])
            self.device_output_sample_rate = int(
                output_device_info["default_samplerate"]
            )

            # Calculate input frame size
            frame_duration_sec = AudioConfig.FRAME_DURATION / 1000
            self._device_input_frame_size = int(
                self.device_input_sample_rate * frame_duration_sec
            )

            logger.info(f"Device input sample rate: {self.device_input_sample_rate}Hz")
            logger.info(f"Device output sample rate: {self.device_output_sample_rate}Hz")
            logger.info(f"Audio output will use a fixed 24kHz sample rate")

            # Create resamplers
            await self._create_resamplers()

            # Set SoundDevice default parameters
            sd.default.samplerate = None
            sd.default.channels = AudioConfig.CHANNELS
            sd.default.dtype = np.int16

            # Create audio streams
            await self._create_streams()

            # Initialize Opus codecs
            # Encoder for 16kHz recording data
            # Decoder for 24kHz playback data
            self.opus_encoder = opuslib.Encoder(
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                opuslib.APPLICATION_AUDIO,
            )
            self.opus_decoder = opuslib.Decoder(
                AudioConfig.OUTPUT_SAMPLE_RATE, AudioConfig.CHANNELS
            )

            logger.info("Audio devices and codecs initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize audio devices: {e}")
            await self.close()
            raise

    async def _create_resamplers(self):
        """
        Create input resampler to convert device sample rate to 16kHz
        Output is fixed at 24kHz, no resampling needed
        """
        if self.device_input_sample_rate != AudioConfig.INPUT_SAMPLE_RATE:
            self.input_resampler = soxr.ResampleStream(
                self.device_input_sample_rate,
                AudioConfig.INPUT_SAMPLE_RATE,
                AudioConfig.CHANNELS,
                dtype="int16",
                quality="QQ",
            )
            logger.info(
                f"Created input resampler: {self.device_input_sample_rate}Hz -> "
                f"{AudioConfig.INPUT_SAMPLE_RATE}Hz"
            )

        logger.info(f"Output uses a fixed 24kHz sample rate")

    async def _create_streams(self):
        """
        Create audio input and output streams
        Input stream uses native device sample rate, output stream is fixed at 24kHz
        """
        try:
            # Recording stream
            self.input_stream = sd.InputStream(
                samplerate=self.device_input_sample_rate,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=self._device_input_frame_size,
                callback=self._input_callback,
                finished_callback=self._input_finished_callback,
                latency="low",
            )

            # Playback stream
            self.output_stream = sd.OutputStream(
                samplerate=AudioConfig.OUTPUT_SAMPLE_RATE,
                channels=AudioConfig.CHANNELS,
                dtype=np.int16,
                blocksize=AudioConfig.OUTPUT_FRAME_SIZE,
                callback=self._output_callback,
                finished_callback=self._output_finished_callback,
                latency="low",
            )

            # Start audio streams
            self.input_stream.start()
            self.output_stream.start()

        except Exception as e:
            logger.error(f"Failed to create audio streams: {e}")
            raise

    def _input_callback(self, indata, frames, time_info, status):
        """
        Recording callback function
        Processes recorded data, resamples to 16kHz, and performs Opus encoding
        """
        if status and "overflow" not in str(status).lower():
            logger.warning(f"Input stream status: {status}")

        if self._is_closing:
            return

        try:
            audio_data = indata.copy().flatten()

            # Resampling process
            if self.input_resampler is not None:
                audio_data = self._process_input_resampling(audio_data)
                if audio_data is None:
                    return

            # Real-time encoding of recorded data
            if self._encoded_audio_callback and len(audio_data) == AudioConfig.INPUT_FRAME_SIZE:
                try:
                    pcm_data = audio_data.astype(np.int16).tobytes()
                    encoded_data = self.opus_encoder.encode(pcm_data, AudioConfig.INPUT_FRAME_SIZE)
                    
                    if encoded_data:
                        self._encoded_audio_callback(encoded_data)
                        
                except Exception as e:
                    logger.warning(f"Real-time recording encoding failed: {e}")

            # Provide data for wake word detection
            self._put_audio_data_safe(self._wakeword_buffer, audio_data.copy())

        except Exception as e:
            logger.error(f"Input callback error: {e}")

    def _process_input_resampling(self, audio_data):
        """
        Input audio resampling process
        Converts device sample rate to 16kHz
        """
        try:
            resampled_data = self.input_resampler.resample_chunk(audio_data, last=False)
            if len(resampled_data) > 0:
                # Add to buffer
                self._resample_input_buffer.extend(resampled_data.astype(np.int16))

            # Check if there is enough data to form a complete frame
            expected_frame_size = AudioConfig.INPUT_FRAME_SIZE
            if len(self._resample_input_buffer) < expected_frame_size:
                return None

            # Take out one frame of data
            frame_data = []
            for _ in range(expected_frame_size):
                frame_data.append(self._resample_input_buffer.popleft())

            return np.array(frame_data, dtype=np.int16)

        except Exception as e:
            logger.error(f"Input resampling failed: {e}")
            return None

    def _put_audio_data_safe(self, queue, audio_data):
        """
        Safely put audio data into the queue
        """
        try:
            queue.put_nowait(audio_data)
        except asyncio.QueueFull:
            # When the queue is full, remove the oldest data
            try:
                queue.get_nowait()
                queue.put_nowait(audio_data)
            except asyncio.QueueEmpty:
                queue.put_nowait(audio_data)

    def _output_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        Playback callback function
        Takes 24kHz audio data from the buffer for playback
        """
        if status:
            if "underflow" not in str(status).lower():
                logger.warning(f"Output stream status: {status}")

        try:
            try:
                # Get audio data from the output buffer
                audio_data = self._output_buffer.get_nowait()

                # Write audio data
                if len(audio_data) >= frames:
                    outdata[:] = audio_data[:frames].reshape(-1, AudioConfig.CHANNELS)
                else:
                    outdata[: len(audio_data)] = audio_data.reshape(-1, AudioConfig.CHANNELS)
                    outdata[len(audio_data) :] = 0

            except asyncio.QueueEmpty:
                # Output silence when there is no data
                outdata.fill(0)

        except Exception as e:
            logger.error(f"Output callback error: {e}")
            outdata.fill(0)


    def _input_finished_callback(self):
        """
        Input stream finished callback
        """
        logger.info("Input stream has finished")

    def _output_finished_callback(self):
        """
        Output stream finished callback
        """
        logger.info("Output stream has finished")

    async def reinitialize_stream(self, is_input=True):
        """
        Reinitialize the audio stream
        """
        if self._is_closing:
            return False if is_input else None

        try:
            if is_input:
                # Rebuild recording stream
                if self.input_stream:
                    self.input_stream.stop()
                    self.input_stream.close()

                self.input_stream = sd.InputStream(
                    samplerate=self.device_input_sample_rate,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=self._device_input_frame_size,
                    callback=self._input_callback,
                    finished_callback=self._input_finished_callback,
                    latency="low",
                )
                self.input_stream.start()
                logger.info("Input stream reinitialized successfully")
                return True
            else:
                # Rebuild playback stream
                if self.output_stream:
                    self.output_stream.stop()
                    self.output_stream.close()

                self.output_stream = sd.OutputStream(
                    samplerate=AudioConfig.OUTPUT_SAMPLE_RATE,
                    channels=AudioConfig.CHANNELS,
                    dtype=np.int16,
                    blocksize=AudioConfig.OUTPUT_FRAME_SIZE,
                    callback=self._output_callback,
                    finished_callback=self._output_finished_callback,
                    latency="low",
                )
                self.output_stream.start()
                logger.info("Output stream reinitialized successfully")
                return None
        except Exception as e:
            stream_type = "Input" if is_input else "Output"
            logger.error(f"{stream_type} stream rebuild failed: {e}")
            if is_input:
                return False
            else:
                raise

    async def get_raw_audio_for_detection(self) -> Optional[bytes]:
        """
        Get raw audio data for wake word detection
        
        Gets data from a dedicated queue, runs independently of recording encoding,
        avoiding data competition issues.

        Returns:
            Optional[bytes]: PCM format audio data, returns None when no data
        """
        try:
            if self._wakeword_buffer.empty():
                return None

            audio_data = self._wakeword_buffer.get_nowait()

            # Convert to bytes format
            if hasattr(audio_data, "tobytes"):
                return audio_data.tobytes()
            elif hasattr(audio_data, "astype"):
                return audio_data.astype("int16").tobytes()
            else:
                return audio_data

        except asyncio.QueueEmpty:
            return None
        except Exception as e:
            logger.error(f"Failed to get wake word audio data: {e}")
            return None

    def set_encoded_audio_callback(self, callback):
        """
        Set the callback function for encoded audio data
        
        Enables real-time encoding mode, where the recording callback directly encodes and passes data,
        eliminating polling latency and improving recording real-time performance.
        
        Args:
            callback: Callback function that receives encoded data parameter, None to disable real-time encoding
        """
        self._encoded_audio_callback = callback
        
        if callback:
            logger.info("✓ Enabled real-time recording encoding mode - recording callback directly encodes and passes")
        else:
            logger.info("✓ Disabled recording encoding callback")

    async def write_audio(self, opus_data: bytes):
        """
        Decode Opus audio data and put it into the playback queue
        Outputs 24kHz PCM data, directly used for playback
        """
        try:
            # Decode Opus to 24kHz PCM data
            pcm_data = self.opus_decoder.decode(
                opus_data, AudioConfig.OUTPUT_FRAME_SIZE
            )

            audio_array = np.frombuffer(pcm_data, dtype=np.int16)

            # Validate data length
            expected_length = AudioConfig.OUTPUT_FRAME_SIZE * AudioConfig.CHANNELS
            if len(audio_array) != expected_length:
                logger.warning(f"Decoded audio length abnormal: {len(audio_array)}, expected: {expected_length}")
                return

            # Put into playback buffer
            self._put_audio_data_safe(self._output_buffer, audio_array)

        except opuslib.OpusError as e:
            logger.warning(f"Opus decoding failed, dropping this frame: {e}")
        except Exception as e:
            logger.warning(f"Audio write failed, dropping this frame: {e}")

    async def wait_for_audio_complete(self, timeout=10.0):
        """
        Wait for audio playback to complete
        """
        start = time.time()
        
        # Wait for the playback queue to be empty
        while not self._output_buffer.empty() and time.time() - start < timeout:
            await asyncio.sleep(0.05)
        
        # Extra wait to ensure the last audio playback is complete
        await asyncio.sleep(0.3)
        
        # Check for timeout
        if not self._output_buffer.empty():
            output_remaining = self._output_buffer.qsize()
            logger.warning(
                f"Audio playback timed out, remaining queue - output: {output_remaining} frames"
            )

    async def clear_audio_queue(self):
        """
        Clear the audio queues
        """
        cleared_count = 0

        # Clear all queues
        queues_to_clear = [
            self._wakeword_buffer,
            self._output_buffer,
        ]

        for queue in queues_to_clear:
            while not queue.empty():
                try:
                    queue.get_nowait()
                    cleared_count += 1
                except asyncio.QueueEmpty:
                    break

        # Clear resample buffer
        if self._resample_input_buffer:
            cleared_count += len(self._resample_input_buffer)
            self._resample_input_buffer.clear()

        # Wait for currently processing audio data to complete
        await asyncio.sleep(0.01)

        if cleared_count > 0:
            logger.info(f"Cleared audio queues, discarded {cleared_count} frames of audio data")

        # Perform garbage collection when data volume is large
        if cleared_count > 100:
            gc.collect()
            logger.debug("Performing garbage collection to release memory")

    async def start_streams(self):
        """
        Start the audio input and output streams
        """
        try:
            if self.input_stream and not self.input_stream.active:
                try:
                    self.input_stream.start()
                except Exception as e:
                    logger.warning(f"Error starting input stream: {e}")
                    await self.reinitialize_stream(is_input=True)

            if self.output_stream and not self.output_stream.active:
                try:
                    self.output_stream.start()
                except Exception as e:
                    logger.warning(f"Error starting output stream: {e}")
                    await self.reinitialize_stream(is_input=False)

            logger.info("Audio streams have started")
        except Exception as e:
            logger.error(f"Failed to start audio streams: {e}")

    async def stop_streams(self):
        """
        Stop the audio input and output streams
        """
        try:
            if self.input_stream and self.input_stream.active:
                self.input_stream.stop()
        except Exception as e:
            logger.warning(f"Failed to stop input stream: {e}")

        try:
            if self.output_stream and self.output_stream.active:
                self.output_stream.stop()
        except Exception as e:
            logger.warning(f"Failed to stop output stream: {e}")

    async def _cleanup_resampler(self, resampler, name):
        """
        Clean up resampler resources
        """
        if resampler:
            try:
                # Process remaining data
                if hasattr(resampler, "resample_chunk"):
                    empty_array = np.array([], dtype=np.int16)
                    resampler.resample_chunk(empty_array, last=True)
            except Exception as e:
                logger.warning(f"Failed to clean up {name} resampler: {e}")

    async def close(self):
        """
        Close the audio codec and release all resources
        """
        if self._is_closing:
            return

        self._is_closing = True
        logger.info("Starting to close the audio codec...")

        try:
            # Clear queues
            await self.clear_audio_queue()

            # Close streams
            if self.input_stream:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except Exception as e:
                    logger.warning(f"Failed to close input stream: {e}")
                finally:
                    self.input_stream = None

            if self.output_stream:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception as e:
                    logger.warning(f"Failed to close output stream: {e}")
                finally:
                    self.output_stream = None

            # Clean up resamplers
            await self._cleanup_resampler(self.input_resampler, "Input")
            self.input_resampler = None

            # Clean up resample buffer
            self._resample_input_buffer.clear()

            # Clean up codecs
            self.opus_encoder = None
            self.opus_decoder = None

            gc.collect()  # Force release of nanobind's C++ objects

            logger.info("Audio resources have been fully released")
        except Exception as e:
            logger.error(f"An error occurred while closing the audio codec: {e}")

    def __del__(self):
        """
        Destructor, checks if resources are properly released
        """
        if not self._is_closing:
            # Cannot use asyncio.create_task in destructor, log a warning instead
            logger.warning("AudioCodec object was destroyed but not properly closed, please ensure close() method is called")
