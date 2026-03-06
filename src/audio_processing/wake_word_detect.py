import asyncio
import difflib
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from vosk import KaldiRecognizer, Model, SetLogLevel

from src.constants.constants import AudioConfig
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WakeWordDetector:
    """Wake Word Detector - English-optimized with fuzzy matching"""

    def __init__(self):
        # Basic properties
        self.audio_codec = None
        self.is_running_flag = False
        self.paused = False
        self.detection_task = None

        # Anti-repeat trigger mechanism
        self.last_detection_time = 0
        self.detection_cooldown = 3.0  # 3-second cooldown

        # Callback functions
        self.on_detected_callback: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # Configuration check
        config = ConfigManager.get_instance()
        if not config.get_config("WAKE_WORD_OPTIONS.USE_WAKE_WORD", False):
            logger.info("Wake word function is disabled")
            self.enabled = False
            return

        # Basic parameter initialization
        self.enabled = True
        self.sample_rate = AudioConfig.INPUT_SAMPLE_RATE

        # Wake word configuration
        self.wake_words = config.get_config(
            "WAKE_WORD_OPTIONS.WAKE_WORDS",
            ["hey assistant", "hello assistant", "hey jarvis", "ok computer"],
        )

        # Pre-process wake words for matching
        self.wake_word_normalized = {
            word: self._normalize_text(word) for word in self.wake_words
        }

        # Matching parameters
        self.similarity_threshold = config.get_config(
            "WAKE_WORD_OPTIONS.SIMILARITY_THRESHOLD", 0.80
        )
        self.max_edit_distance = config.get_config(
            "WAKE_WORD_OPTIONS.MAX_EDIT_DISTANCE", 2
        )

        # Performance optimization: cache recent recognition results
        self._recent_texts = []
        self._max_recent_cache = 10

        # Initialize model
        self._init_model(config)

        # Validate configuration
        self._validate_config()

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text for comparison: lowercase, strip punctuation, collapse whitespace."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _init_model(self, config):
        """Initialize the speech recognition model."""
        try:
            model_path = self._get_model_path(config)
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model path does not exist: {model_path}")

            logger.info(f"Loading speech recognition model: {model_path}")
            SetLogLevel(-1)
            self.model = Model(model_path=model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
            logger.info(f"Model loaded, {len(self.wake_words)} wake words configured: {self.wake_words}")

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            self.enabled = False

    def _get_model_path(self, config):
        """Get the model path."""
        from src.utils.resource_finder import resource_finder

        model_name = config.get_config(
            "WAKE_WORD_OPTIONS.MODEL_PATH", "vosk-model-small-en-us-0.22"
        )

        model_path = Path(model_name)

        # Return absolute path directly
        if model_path.is_absolute() and model_path.exists():
            return str(model_path)

        # Standardize to models subdirectory path
        if len(model_path.parts) == 1:
            model_path = Path("models") / model_path

        # Find using resource_finder
        model_dir_path = resource_finder.find_directory(model_path)
        if model_dir_path:
            return str(model_dir_path)

        # Find in models directory
        models_dir = resource_finder.find_models_dir()
        if models_dir:
            model_name_only = (
                model_path.name if len(model_path.parts) > 1 else model_path
            )
            direct_model_path = models_dir / model_name_only
            if direct_model_path.exists():
                return str(direct_model_path)

            for item in models_dir.iterdir():
                if item.is_dir() and item.name == model_name_only:
                    return str(item)

        # Use default path
        project_root = resource_finder.get_project_root()
        default_path = project_root / model_path
        logger.warning(f"Model not found, will use default path: {default_path}")
        return str(default_path)

    def _calculate_similarity(self, recognized_text: str, wake_word: str) -> float:
        """Calculate similarity between recognized text and a wake word using multiple strategies."""
        norm_text = self._normalize_text(recognized_text)
        norm_wake = self.wake_word_normalized.get(wake_word, self._normalize_text(wake_word))

        if not norm_text or not norm_wake:
            return 0.0

        # 1. Exact substring match
        if norm_wake in norm_text:
            return 1.0

        # 2. Check if wake word words appear in the text in order
        wake_words = norm_wake.split()
        text_words = norm_text.split()
        if self._words_in_order(wake_words, text_words):
            return 0.95

        # 3. SequenceMatcher on the full strings
        seq_sim = difflib.SequenceMatcher(None, norm_text, norm_wake).ratio()

        # 4. Word-level matching for multi-word wake words
        if len(wake_words) > 1:
            matched = sum(1 for w in wake_words if w in text_words)
            word_sim = matched / len(wake_words)
            seq_sim = max(seq_sim, word_sim)

        # 5. Sliding window over text for partial matches
        if len(norm_text) > len(norm_wake):
            window_size = len(norm_wake)
            best_window = 0.0
            for i in range(len(norm_text) - window_size + 1):
                window = norm_text[i:i + window_size]
                window_sim = difflib.SequenceMatcher(None, window, norm_wake).ratio()
                best_window = max(best_window, window_sim)
            seq_sim = max(seq_sim, best_window)

        # 6. Edit distance for short wake words
        if len(norm_wake) <= 15:
            edit_dist = self._levenshtein_distance(norm_text, norm_wake)
            max_allowed = min(self.max_edit_distance, len(norm_wake) // 3)
            if edit_dist <= max_allowed:
                edit_sim = 1.0 - (edit_dist / max(len(norm_wake), 1))
                seq_sim = max(seq_sim, edit_sim)

        return seq_sim

    @staticmethod
    def _words_in_order(pattern_words, text_words):
        """Check if all pattern words appear in text_words in order."""
        idx = 0
        for tw in text_words:
            if idx < len(pattern_words) and tw == pattern_words[idx]:
                idx += 1
        return idx == len(pattern_words)

    @staticmethod
    def _levenshtein_distance(s1, s2):
        """Calculate the Levenshtein distance."""
        if len(s1) < len(s2):
            return WakeWordDetector._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def on_detected(self, callback: Callable):
        """Set the callback function for when a wake word is detected."""
        self.on_detected_callback = callback

    async def start(self, audio_codec) -> bool:
        """Start the wake word detector."""
        if not self.enabled:
            logger.warning("Wake word function is not enabled")
            return False

        try:
            self.audio_codec = audio_codec
            self.is_running_flag = True
            self.paused = False

            self.detection_task = asyncio.create_task(self._detection_loop())

            logger.info("Wake word detector started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start wake word detector: {e}")
            self.enabled = False
            return False

    async def _detection_loop(self):
        """Detection loop."""
        error_count = 0
        MAX_ERRORS = 5

        while self.is_running_flag:
            try:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue

                if not self.audio_codec:
                    await asyncio.sleep(0.5)
                    continue

                await self._process_audio()
                await asyncio.sleep(0.02)
                error_count = 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Wake word detection loop error ({error_count}/{MAX_ERRORS}): {e}")
                if self.on_error:
                    try:
                        if asyncio.iscoroutinefunction(self.on_error):
                            await self.on_error(e)
                        else:
                            self.on_error(e)
                    except Exception as callback_error:
                        logger.error(f"Failed to execute error callback: {callback_error}")

                if error_count >= MAX_ERRORS:
                    logger.critical("Maximum number of errors reached, stopping detection")
                    break

                await asyncio.sleep(1)

    async def _process_audio(self):
        """Process audio data."""
        try:
            if not self.audio_codec:
                return

            data = await self.audio_codec.get_raw_audio_for_detection()
            if not data:
                return

            await self._process_audio_data(data)

        except Exception as e:
            logger.debug(f"Audio processing error: {e}")

    async def _process_audio_data(self, data):
        """Process audio data for wake word detection."""
        try:
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                if text := result.get("text", "").strip():
                    if len(text) >= 2:
                        await self._check_wake_word_text(text)

            # Check partial results periodically
            if hasattr(self, "_partial_check_counter"):
                self._partial_check_counter += 1
            else:
                self._partial_check_counter = 0

            if self._partial_check_counter % 3 == 0:
                partial = (
                    json.loads(self.recognizer.PartialResult())
                    .get("partial", "")
                    .strip()
                )
                if partial and len(partial) >= 2:
                    await self._check_wake_word_text(partial)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
        except Exception as e:
            logger.error(f"Audio data processing error: {e}")

    async def _check_wake_word_text(self, text):
        """Check for wake words in the recognized text."""
        if not text or not text.strip():
            return

        # Anti-repeat trigger check
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_cooldown:
            return

        # Avoid processing the same text repeatedly
        if text in self._recent_texts:
            return

        self._recent_texts.append(text)
        if len(self._recent_texts) > self._max_recent_cache:
            self._recent_texts.pop(0)

        best_match = None
        best_similarity = 0.0

        for wake_word in self.wake_words:
            similarity = self._calculate_similarity(text, wake_word)

            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = wake_word

        if best_match:
            self.last_detection_time = current_time
            logger.info(
                f"Detected wake word '{best_match}' "
                f"(similarity: {best_similarity:.3f}, text: '{text}')"
            )

            await self._trigger_callbacks(best_match, text)
            self.recognizer.Reset()
            self._recent_texts.clear()

    async def _trigger_callbacks(self, wake_word, text):
        """Trigger callback functions."""
        if self.on_detected_callback:
            try:
                if asyncio.iscoroutinefunction(self.on_detected_callback):
                    await self.on_detected_callback(wake_word, text)
                else:
                    self.on_detected_callback(wake_word, text)
            except Exception as e:
                logger.error(f"Wake word callback execution failed: {e}")

    async def stop(self):
        """Stop the detector."""
        self.is_running_flag = False

        if self.detection_task:
            self.detection_task.cancel()
            try:
                await self.detection_task
            except asyncio.CancelledError:
                pass

        logger.info("Wake word detector stopped")

    async def pause(self):
        """Pause detection."""
        self.paused = True

    async def resume(self):
        """Resume detection."""
        self.paused = False

    def is_running(self) -> bool:
        """Check if it is running."""
        return self.is_running_flag and not self.paused

    def _validate_config(self):
        """Validate configuration parameters."""
        if not self.enabled:
            return

        if not 0.1 <= self.similarity_threshold <= 1.0:
            logger.warning(
                f"Similarity threshold {self.similarity_threshold} out of range, resetting to 0.80"
            )
            self.similarity_threshold = 0.80

        if self.max_edit_distance < 0 or self.max_edit_distance > 5:
            logger.warning(
                f"Max edit distance {self.max_edit_distance} out of range, resetting to 2"
            )
            self.max_edit_distance = 2

        if not self.wake_words:
            logger.error("No wake words configured")
            self.enabled = False
            return

        for word in self.wake_words:
            if len(word) < 2:
                logger.warning(f"Wake word '{word}' is too short, may cause false positives")
            elif len(word) > 30:
                logger.warning(f"Wake word '{word}' is too long, may affect recognition accuracy")

        logger.info(
            f"Config validated - Threshold: {self.similarity_threshold}, "
            f"Edit distance: {self.max_edit_distance}, "
            f"Wake words: {self.wake_words}"
        )

    def get_performance_stats(self):
        """Get performance statistics."""
        return {
            "enabled": self.enabled,
            "wake_words_count": len(self.wake_words),
            "similarity_threshold": self.similarity_threshold,
            "max_edit_distance": self.max_edit_distance,
            "recent_texts_count": len(self._recent_texts),
        }

    def clear_cache(self):
        """Clear the cache."""
        self._recent_texts.clear()
        logger.info("Cache cleared")
