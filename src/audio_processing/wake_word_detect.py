import asyncio
import difflib
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

from pypinyin import Style, lazy_pinyin
from vosk import KaldiRecognizer, Model, SetLogLevel

from src.constants.constants import AudioConfig
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WakeWordDetector:
    """Wake Word Detector - Advanced Matching Algorithm Version"""

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
            ["Hello Xiaoming", "Hello Xiaozhi", "Hello Xiaotian", "Xiaoai Speaker", "Jarvis"],
        )

        # Pre-calculate pinyin variants to improve performance
        self.wake_word_patterns = self._build_wake_word_patterns()

        # Matching parameters
        self.similarity_threshold = config.get_config(
            "WAKE_WORD_OPTIONS.SIMILARITY_THRESHOLD", 0.85
        )
        self.max_edit_distance = config.get_config(
            "WAKE_WORD_OPTIONS.MAX_EDIT_DISTANCE", 1
        )

        # Performance optimization: cache recent recognition results
        self._recent_texts = []
        self._max_recent_cache = 10

        # Initialize model
        self._init_model(config)
        
        # Validate configuration
        self._validate_config()

    def _build_wake_word_patterns(self):
        """
        Build pinyin patterns for wake words, including multiple variants.
        """
        patterns = {}
        for word in self.wake_words:
            # Standard pinyin (without tones)
            standard_pinyin = "".join(lazy_pinyin(word, style=Style.NORMAL))

            # Pinyin with first letter
            initials_pinyin = "".join(lazy_pinyin(word, style=Style.FIRST_LETTER))

            # Pinyin with tones
            tone_pinyin = "".join(lazy_pinyin(word, style=Style.TONE))

            # Pinyin finals
            finals_pinyin = "".join(lazy_pinyin(word, style=Style.FINALS))

            patterns[word] = {
                "standard": standard_pinyin.lower(),
                "initials": initials_pinyin.lower(),
                "tone": tone_pinyin.lower(),
                "finals": finals_pinyin.lower(),
                "original": word,
                "length": len(standard_pinyin),
            }

        return patterns

    @lru_cache(maxsize=128)
    def _get_text_pinyin_variants(self, text):
        """
        Get pinyin variants of text (with cache).
        """
        if not text or not text.strip():
            return {}

        # Clean text
        cleaned_text = re.sub(r"[^\u4e00-\u9fff\w]", "", text)
        if not cleaned_text:
            return {}

        return {
            "standard": "".join(lazy_pinyin(cleaned_text, style=Style.NORMAL)).lower(),
            "initials": "".join(
                lazy_pinyin(cleaned_text, style=Style.FIRST_LETTER)
            ).lower(),
            "tone": "".join(lazy_pinyin(cleaned_text, style=Style.TONE)).lower(),
            "finals": "".join(lazy_pinyin(cleaned_text, style=Style.FINALS)).lower(),
        }

    def _init_model(self, config):
        """
        Initialize the speech recognition model.
        """
        try:
            model_path = self._get_model_path(config)
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model path does not exist: {model_path}")

            logger.info(f"Loading speech recognition model: {model_path}")
            SetLogLevel(-1)
            self.model = Model(model_path=model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
            logger.info(f"Model loaded, {len(self.wake_words)} wake words configured")

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            self.enabled = False

    def _get_model_path(self, config):
        """
        Get the model path.
        """
        from src.utils.resource_finder import resource_finder

        model_name = config.get_config(
            "WAKE_WORD_OPTIONS.MODEL_PATH", "vosk-model-small-cn-0.22"
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

            # Traverse subdirectories to find
            for item in models_dir.iterdir():
                if item.is_dir() and item.name == model_name_only:
                    return str(item)

        # Use default path
        project_root = resource_finder.get_project_root()
        default_path = project_root / model_path
        logger.warning(f"Model not found, will use default path: {default_path}")
        return str(default_path)

    def _calculate_similarity(self, text_variants, pattern):
        """
        Calculate the similarity between the text and the wake word pattern.
        """
        max_similarity = 0.0
        best_match_type = None

        # Check matching for various pinyin variants
        for variant_type in ["standard", "tone", "initials", "finals"]:
            text_variant = text_variants.get(variant_type, "")
            pattern_variant = pattern.get(variant_type, "")

            if not text_variant or not pattern_variant:
                continue

            # 1. Exact match (highest priority)
            if pattern_variant in text_variant:
                return 1.0, f"exact_{variant_type}"

            # 2. SequenceMatcher similarity
            similarity = difflib.SequenceMatcher(
                None, text_variant, pattern_variant
            ).ratio()

            # 3. Edit distance matching (for short text)
            if len(pattern_variant) <= 10:
                edit_distance = self._levenshtein_distance(
                    text_variant, pattern_variant
                )
                max_allowed_distance = min(
                    self.max_edit_distance, len(pattern_variant) // 2
                )
                if edit_distance <= max_allowed_distance:
                    edit_similarity = 1.0 - (edit_distance / len(pattern_variant))
                    similarity = max(similarity, edit_similarity)

            # 4. Subsequence matching (for initials)
            if variant_type == "initials" and len(pattern_variant) >= 2:
                if self._is_subsequence(pattern_variant, text_variant):
                    similarity = max(similarity, 0.80)

            if similarity > max_similarity:
                max_similarity = similarity
                best_match_type = variant_type

        return max_similarity, best_match_type

    def _levenshtein_distance(self, s1, s2):
        """
        Calculate the Levenshtein distance.
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

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

    def _is_subsequence(self, pattern, text):
        """
        Check if pattern is a subsequence of text.
        """
        i = 0
        for char in text:
            if i < len(pattern) and char == pattern[i]:
                i += 1
        return i == len(pattern)

    def on_detected(self, callback: Callable):
        """
        Set the callback function for when a wake word is detected.
        """
        self.on_detected_callback = callback

    async def start(self, audio_codec) -> bool:
        """
        Start the wake word detector.
        """
        if not self.enabled:
            logger.warning("Wake word function is not enabled")
            return False

        try:
            self.audio_codec = audio_codec
            self.is_running_flag = True
            self.paused = False

            # Start detection task
            self.detection_task = asyncio.create_task(self._detection_loop())

            logger.info("Asynchronous wake word detector started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start asynchronous wake word detector: {e}")
            self.enabled = False
            return False

    async def _detection_loop(self):
        """
        Detection loop.
        """
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

                # Get data from the audio codec and process it
                await self._process_audio()

                # Short delay to avoid excessive CPU usage
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

                await asyncio.sleep(1)  # Delay before retrying after an error

    async def _process_audio(self):
        """
        Process audio data - using the old full processing logic.
        """
        try:
            # Use the public interface of AudioCodec to get audio data
            if not self.audio_codec:
                return

            # Get raw audio data for wake word detection
            data = await self.audio_codec.get_raw_audio_for_detection()
            if not data:
                return

            # Process audio data
            await self._process_audio_data(data)

        except Exception as e:
            logger.debug(f"Audio processing error: {e}")

    async def _process_audio_data(self, data):
        """
        Asynchronously process audio data.
        """
        try:
            # Process full recognition result
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                if text := result.get("text", "").strip():
                    # Filter out text that is too short to reduce false positives
                    if len(text) >= 3:
                        await self._check_wake_word_text(text)

            # Process partial recognition result (at a lower frequency)
            if hasattr(self, "_partial_check_counter"):
                self._partial_check_counter += 1
            else:
                self._partial_check_counter = 0

            # Check partial result only every 3 times
            if self._partial_check_counter % 3 == 0:
                partial = (
                    json.loads(self.recognizer.PartialResult())
                    .get("partial", "")
                    .strip()
                )
                if partial and len(partial) >= 3:
                    await self._check_wake_word_text(partial)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
        except Exception as e:
            logger.error(f"Audio data processing error: {e}")

    async def _check_wake_word_text(self, text):
        """
        Check for wake words in the text.
        """
        if not text or not text.strip():
            return

        # Anti-repeat trigger check
        current_time = time.time()
        if current_time - self.last_detection_time < self.detection_cooldown:
            return

        # Avoid processing the same text repeatedly
        if text in self._recent_texts:
            return

        # Update recent text cache
        self._recent_texts.append(text)
        if len(self._recent_texts) > self._max_recent_cache:
            self._recent_texts.pop(0)

        # Get pinyin variants of the text
        text_variants = self._get_text_pinyin_variants(text)
        if not text_variants or not any(text_variants.values()):
            return

        best_match = None
        best_similarity = 0.0
        best_match_info = None

        # Check each wake word pattern
        for wake_word, pattern in self.wake_word_patterns.items():
            similarity, match_type = self._calculate_similarity(text_variants, pattern)

            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = wake_word
                best_match_info = match_type

        # Trigger detection
        if best_match:
            self.last_detection_time = current_time
            logger.info(
                f"Detected wake word '{best_match}' "
                f"(Similarity: {best_similarity:.3f}, Match type: {best_match_info})"
            )

            await self._trigger_callbacks(best_match, text)
            self.recognizer.Reset()
            # Clear cache to avoid repeated triggers
            self._recent_texts.clear()

    async def _trigger_callbacks(self, wake_word, text):
        """
        Trigger callback functions.
        """
        if self.on_detected_callback:
            try:
                if asyncio.iscoroutinefunction(self.on_detected_callback):
                    await self.on_detected_callback(wake_word, text)
                else:
                    self.on_detected_callback(wake_word, text)
            except Exception as e:
                logger.error(f"Wake word callback execution failed: {e}")



    async def stop(self):
        """
        Stop the detector.
        """
        self.is_running_flag = False

        if self.detection_task:
            self.detection_task.cancel()
            try:
                await self.detection_task
            except asyncio.CancelledError:
                pass

        logger.info("Wake word detector stopped")

    async def pause(self):
        """
        Pause detection.
        """
        self.paused = True

    async def resume(self):
        """
        Resume detection.
        """
        self.paused = False

    def is_running(self) -> bool:
        """
        Check if it is running.
        """
        return self.is_running_flag and not self.paused

    def _validate_config(self):
        """
        Validate configuration parameters.
        """
        if not self.enabled:
            return

        # Validate similarity threshold
        if not 0.1 <= self.similarity_threshold <= 1.0:
            logger.warning(
                f"Similarity threshold {self.similarity_threshold} is out of reasonable range, resetting to 0.85"
            )
            self.similarity_threshold = 0.85

        # Validate edit distance
        if self.max_edit_distance < 0 or self.max_edit_distance > 5:
            logger.warning(
                f"Max edit distance {self.max_edit_distance} is out of reasonable range, resetting to 1"
            )
            self.max_edit_distance = 1

        # Validate wake words
        if not self.wake_words:
            logger.error("No wake words configured")
            self.enabled = False
            return

        # Check wake word length
        for word in self.wake_words:
            if len(word) < 2:
                logger.warning(f"Wake word '{word}' is too short, may cause false positives")
            elif len(word) > 10:
                logger.warning(f"Wake word '{word}' is too long, may affect recognition accuracy")

        logger.info(
            f"Configuration validation complete - Threshold: {self.similarity_threshold}, Edit distance: {self.max_edit_distance}"
        )

    def get_performance_stats(self):
        """
        Get performance statistics.
        """
        cache_info = self._get_text_pinyin_variants.cache_info()
        return {
            "enabled": self.enabled,
            "wake_words_count": len(self.wake_words),
            "similarity_threshold": self.similarity_threshold,
            "max_edit_distance": self.max_edit_distance,
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "recent_texts_count": len(self._recent_texts),
        }

    def clear_cache(self):
        """
        Clear the cache.
        """
        self._get_text_pinyin_variants.cache_clear()
        self._recent_texts.clear()
        logger.info("Cache cleared")

