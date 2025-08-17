import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import pygame
import requests

from src.constants.constants import AudioConfig
from src.iot.thing import Parameter, Thing, ValueType
from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root

logger = get_logger(__name__)


class MusicPlayer(Thing):
    """Music Player - Designed for IoT devices

    Only core functions are retained: search, play, pause, stop, seek
    """

    def __init__(self):
        super().__init__("MusicPlayer", "Music player, supports online music playback control")

        # Initialize pygame mixer
        pygame.mixer.init(
            frequency=AudioConfig.OUTPUT_SAMPLE_RATE, channels=AudioConfig.CHANNELS
        )

        # Core playback state
        self.current_song = ""
        self.current_url = ""
        self.song_id = ""
        self.total_duration = 0
        self.is_playing = False
        self.paused = False
        self.current_position = 0
        self.start_play_time = 0

        # Lyrics related
        self.lyrics = []  # List of lyrics, format: [(time, text), ...]
        self.current_lyric_index = -1  # Current lyric index

        # Cache directory settings
        self.cache_dir = Path(get_project_root()) / "cache" / "music"
        self.temp_cache_dir = self.cache_dir / "temp"
        self._init_cache_dirs()

        # API configuration
        self.config = {
            "SEARCH_URL": "http://search.kuwo.cn/r.s",
            "PLAY_URL": "http://api.xiaodaokg.com/kuwo.php",
            "LYRIC_URL": "http://m.kuwo.cn/newh5/singles/songinfoandlrc",
            "HEADERS": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " "AppleWebKit/537.36"
                ),
                "Accept": "*/*",
                "Connection": "keep-alive",
            },
        }

        # Clean temporary cache
        self._clean_temp_cache()

        # Get application instance
        self.app = None
        self._initialize_app_reference()

        logger.info("Simplified music player initialization complete")
        self._register_properties_and_methods()

    def _initialize_app_reference(self):
        """
        Initialize application reference.
        """
        try:
            from src.application import Application

            self.app = Application.get_instance()
        except Exception as e:
            logger.warning(f"Failed to get Application instance: {e}")
            self.app = None

    def _init_cache_dirs(self):
        """
        Initialize cache directories.
        """
        try:
            # Create main cache directory
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # Create temporary cache directory
            self.temp_cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Music cache directory initialized: {self.cache_dir}")
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
            # Fall back to system temporary directory
            self.cache_dir = Path(tempfile.gettempdir()) / "xiaozhi_music_cache"
            self.temp_cache_dir = self.cache_dir / "temp"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.temp_cache_dir.mkdir(parents=True, exist_ok=True)

    def _clean_temp_cache(self):
        """
        Clean temporary cache files.
        """
        try:
            # Clear all files in the temporary cache directory
            for file_path in self.temp_cache_dir.glob("*"):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"Deleted temporary cache file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary cache file: {file_path.name}, {e}")

            logger.info("Temporary music cache cleanup complete")
        except Exception as e:
            logger.error(f"Failed to clean temporary cache directory: {e}")

    def _register_properties_and_methods(self):
        """
        Register properties and methods.
        """
        # Properties
        self.add_property("current_song", "Current Song", self.get_current_song)
        self.add_property("is_playing", "Is Playing", self.get_is_playing)
        self.add_property("paused", "Is Paused", self.get_paused)
        self.add_property("duration", "Total Duration", self.get_duration)
        self.add_property("position", "Current Position", self.get_position)
        self.add_property("progress", "Playback Progress (percentage)", self.get_progress)

        # Methods
        self.add_method(
            "SearchAndPlay",
            "Search and Play Song",
            [Parameter("song_name", "Song Name", ValueType.STRING, True)],
            self.search_and_play,
        )

        self.add_method("PlayPause", "Play/Pause Toggle", [], self.play_pause)

        self.add_method("Stop", "Stop Playback", [], self.stop)

        self.add_method(
            "Seek",
            "Seek to specified position",
            [Parameter("position", "Position (seconds)", ValueType.NUMBER, True)],
            self.seek,
        )

        self.add_method("GetLyrics", "Get Current Song Lyrics", [], self.get_lyrics)

    # Property getter methods
    async def get_current_song(self):
        return self.current_song

    async def get_is_playing(self):
        return self.is_playing

    async def get_paused(self):
        return self.paused

    async def get_duration(self):
        return self.total_duration

    async def get_position(self):
        if not self.is_playing or self.paused:
            return self.current_position

        current_pos = min(self.total_duration, time.time() - self.start_play_time)

        # Check if playback is complete
        if current_pos >= self.total_duration and self.total_duration > 0:
            await self._handle_playback_finished()

        return current_pos

    async def get_progress(self):
        """
        Get playback progress percentage.
        """
        if self.total_duration <= 0:
            return 0
        position = await self.get_position()
        return round(position * 100 / self.total_duration, 1)

    async def _handle_playback_finished(self):
        """
        Handle playback finished.
        """
        if self.is_playing:
            logger.info(f"Song playback finished: {self.current_song}")
            pygame.mixer.music.stop()
            self.is_playing = False
            self.paused = False
            self.current_position = self.total_duration

            # Update UI to show completion status
            if self.app and hasattr(self.app, "set_chat_message"):
                dur_str = self._format_time(self.total_duration)
                await self._safe_update_ui(f"Playback finished: {self.current_song} [{dur_str}]")

    # Core methods
    async def search_and_play(self, params):
        """
        Search and play song.
        """
        song_name = params["song_name"].get_value()

        try:
            # Search for song
            song_id, url = await self._search_song(song_name)
            if not song_id or not url:
                return {"status": "error", "message": f"Song not found: {song_name}"}

            # Play song
            success = await self._play_url(url)
            if success:
                return {
                    "status": "success",
                    "message": f"Now playing: {self.current_song}",
                }
            else:
                return {"status": "error", "message": "Playback failed"}

        except Exception as e:
            logger.error(f"Search and play failed: {e}")
            return {"status": "error", "message": f"Operation failed: {str(e)}"}

    async def play_pause(self, params):
        """
        Play/pause toggle.
        """
        try:
            if not self.is_playing and self.current_url:
                # Replay
                success = await self._play_url(self.current_url)
                return {
                    "status": "success" if success else "error",
                    "message": (
                        f"Starting playback: {self.current_song}" if success else "Playback failed"
                    ),
                }

            elif self.is_playing and self.paused:
                # Resume playback
                pygame.mixer.music.unpause()
                self.paused = False
                self.start_play_time = time.time() - self.current_position

                # Update UI
                if self.app and hasattr(self.app, "set_chat_message"):
                    await self._safe_update_ui(f"Resuming playback: {self.current_song}")

                return {
                    "status": "success",
                    "message": f"Resuming playback: {self.current_song}",
                }

            elif self.is_playing and not self.paused:
                # Pause playback
                pygame.mixer.music.pause()
                self.paused = True
                self.current_position = time.time() - self.start_play_time

                # Update UI
                if self.app and hasattr(self.app, "set_chat_message"):
                    pos_str = self._format_time(self.current_position)
                    dur_str = self._format_time(self.total_duration)
                    await self._safe_update_ui(
                        f"Paused: {self.current_song} [{pos_str}/{dur_str}]"
                    )

                return {"status": "success", "message": f"Paused: {self.current_song}"}

            else:
                return {"status": "error", "message": "No song to play"}

        except Exception as e:
            logger.error(f"Play/pause operation failed: {e}")
            return {"status": "error", "message": f"Operation failed: {str(e)}"}

    async def stop(self, params):
        """
        Stop playback.
        """
        try:
            if not self.is_playing:
                return {"status": "info", "message": "No song is currently playing"}

            pygame.mixer.music.stop()
            current_song = self.current_song
            self.is_playing = False
            self.paused = False
            self.current_position = 0

            # Update UI
            if self.app and hasattr(self.app, "set_chat_message"):
                await self._safe_update_ui(f"Stopped: {current_song}")

            return {"status": "success", "message": f"Stopped: {current_song}"}

        except Exception as e:
            logger.error(f"Failed to stop playback: {e}")
            return {"status": "error", "message": f"Stop failed: {str(e)}"}

    async def seek(self, params):
        """
        Seek to specified position.
        """
        try:
            position = params["position"].get_value()

            if not self.is_playing:
                return {"status": "error", "message": "No song is currently playing"}

            position = max(0, min(position, self.total_duration))
            self.current_position = position
            self.start_play_time = time.time() - position

            pygame.mixer.music.rewind()
            pygame.mixer.music.set_pos(position)

            if self.paused:
                pygame.mixer.music.pause()

            # Update UI
            pos_str = self._format_time(position)
            dur_str = self._format_time(self.total_duration)
            if self.app and hasattr(self.app, "set_chat_message"):
                await self._safe_update_ui(f"Seeked to: {pos_str}/{dur_str}")

            return {"status": "success", "message": f"Seeked to: {position:.1f} seconds"}

        except Exception as e:
            logger.error(f"Seek failed: {e}")
            return {"status": "error", "message": f"Seek failed: {str(e)}"}

    async def get_lyrics(self, params):
        """
        Get current song lyrics.
        """
        if not self.lyrics:
            return {"status": "info", "message": "Current song has no lyrics", "lyrics": []}

        # Extract lyric text, convert to list
        lyrics_text = []
        for time_sec, text in self.lyrics:
            time_str = self._format_time(time_sec)
            lyrics_text.append(f"[{time_str}] {text}")

        return {
            "status": "success",
            "message": f"Got {len(self.lyrics)} lines of lyrics",
            "lyrics": lyrics_text,
        }

    # Internal methods
    async def _search_song(self, song_name: str) -> Tuple[str, str]:
        """
        Search for song to get ID and URL.
        """
        try:
            # Build search parameters
            params = {
                "all": song_name,
                "ft": "music",
                "newsearch": "1",
                "alflac": "1",
                "itemset": "web_2013",
                "client": "kt",
                "cluster": "0",
                "pn": "0",
                "rn": "1",
                "vermerge": "1",
                "rformat": "json",
                "encoding": "utf8",
                "show_copyright_off": "1",
                "pcmp4": "1",
                "ver": "mbox",
                "vipver": "MUSIC_8.7.6.0.BCS31",
                "plat": "pc",
                "devid": "0",
            }

            # Search for song
            response = await asyncio.to_thread(
                requests.get,
                self.config["SEARCH_URL"],
                params=params,
                headers=self.config["HEADERS"],
                timeout=10,
            )
            response.raise_for_status()

            # Parse response
            text = response.text.replace("'", '"')

            # Extract song ID
            song_id = self._extract_value(text, '"DC_TARGETID":"', '"')
            if not song_id:
                return "", ""

            # Extract song information
            title = self._extract_value(text, '"NAME":"', '"') or song_name
            artist = self._extract_value(text, '"ARTIST":"', '"')
            album = self._extract_value(text, '"ALBUM":"', '"')
            duration_str = self._extract_value(text, '"DURATION":"', '"')

            if duration_str:
                try:
                    self.total_duration = int(duration_str)
                except ValueError:
                    self.total_duration = 0

            # Set display name
            display_name = title
            if artist:
                display_name = f"{title} - {artist}"
                if album:
                    display_name += f" ({album})"
            self.current_song = display_name
            self.song_id = song_id

            # Get playback URL
            play_url = f"{self.config['PLAY_URL']}?ID={song_id}"
            url_response = await asyncio.to_thread(
                requests.get, play_url, headers=self.config["HEADERS"], timeout=10
            )
            url_response.raise_for_status()

            play_url_text = url_response.text.strip()
            if play_url_text and play_url_text.startswith("http"):
                # Fetch lyrics
                await self._fetch_lyrics(song_id)
                return song_id, play_url_text

            return song_id, ""

        except Exception as e:
            logger.error(f"Failed to search for song: {e}")
            return "", ""

    async def _play_url(self, url: str) -> bool:
        """
        Play specified URL.
        """
        try:
            # Stop current playback
            if self.is_playing:
                pygame.mixer.music.stop()

            # Check cache or download
            file_path = await self._get_or_download_file(url)
            if not file_path:
                return False

            # Load and play
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()

            self.current_url = url
            self.is_playing = True
            self.paused = False
            self.current_position = 0
            self.start_play_time = time.time()
            self.current_lyric_index = -1  # Reset lyric index

            logger.info(f"Starting playback: {self.current_song}")

            # Update UI
            if self.app and hasattr(self.app, "set_chat_message"):
                await self._safe_update_ui(f"Now playing: {self.current_song}")

            # Start lyrics update task
            asyncio.create_task(self._lyrics_update_task())

            return True

        except Exception as e:
            logger.error(f"Playback failed: {e}")
            return False

    async def _get_or_download_file(self, url: str) -> Optional[Path]:
        """Get or download file.

        First check the cache, if not in cache, then download
        """
        try:
            # Use song ID as cache filename
            cache_filename = f"{self.song_id}.mp3"
            cache_path = self.cache_dir / cache_filename

            # Check if cache exists
            if cache_path.exists():
                logger.info(f"Using cache: {cache_path}")
                return cache_path

            # Cache does not exist, download needed
            return await self._download_file(url, cache_filename)

        except Exception as e:
            logger.error(f"Failed to get file: {e}")
            return None

    async def _download_file(self, url: str, filename: str) -> Optional[Path]:
        """Download file to cache directory.

        First download to a temporary directory, then move to the official cache directory after completion
        """
        temp_path = None
        try:
            # Create temporary file path
            temp_path = self.temp_cache_dir / f"temp_{int(time.time())}_{filename}"

            # Asynchronous download
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=self.config["HEADERS"],
                stream=True,
                timeout=30,
            )
            response.raise_for_status()

            # Write to temporary file
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Download complete, move to official cache directory
            cache_path = self.cache_dir / filename
            shutil.move(str(temp_path), str(cache_path))

            logger.info(f"Music downloaded and cached: {cache_path}")
            return cache_path

        except Exception as e:
            logger.error(f"Download failed: {e}")
            # Clean up temporary file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                    logger.debug(f"Cleaned up temporary download file: {temp_path}")
                except Exception:
                    pass
            return None

    async def _fetch_lyrics(self, song_id: str):
        """
        Fetch lyrics.
        """
        try:
            # Reset lyrics
            self.lyrics = []

            # Build lyrics API request
            lyric_url = self.config.get("LYRIC_URL")
            lyric_api_url = f"{lyric_url}?musicId={song_id}"
            logger.info(f"Fetching lyrics URL: {lyric_api_url}")

            response = await asyncio.to_thread(
                requests.get, lyric_api_url, headers=self.config["HEADERS"], timeout=10
            )
            response.raise_for_status()

            # Parse JSON
            data = response.json()

            # Parse lyrics
            if (
                data.get("status") == 200
                and data.get("data")
                and data["data"].get("lrclist")
            ):
                lrc_list = data["data"]["lrclist"]

                for lrc in lrc_list:
                    time_sec = float(lrc.get("time", "0"))
                    text = lrc.get("lineLyric", "").strip()

                    # Skip empty lyrics and meta-information lyrics
                    if (
                        text
                        and not text.startswith("作词")
                        and not text.startswith("作曲")
                        and not text.startswith("编曲")
                    ):
                        self.lyrics.append((time_sec, text))

                logger.info(f"Successfully fetched lyrics, {len(self.lyrics)} lines in total")
            else:
                logger.warning(f"Failed to fetch lyrics or lyrics format error: {data.get('msg', '')}")

        except Exception as e:
            logger.error(f"Failed to fetch lyrics: {e}")

    async def _lyrics_update_task(self):
        """
        Lyrics update task.
        """
        if not self.lyrics:
            return

        try:
            while self.is_playing:
                if self.paused:
                    await asyncio.sleep(0.5)
                    continue

                current_time = time.time() - self.start_play_time

                # Check if playback is complete
                if current_time >= self.total_duration:
                    await self._handle_playback_finished()
                    break

                # Find the lyric corresponding to the current time
                current_index = self._find_current_lyric_index(current_time)

                # If the lyric index has changed, update the display
                if current_index != self.current_lyric_index:
                    await self._display_current_lyric(current_index)

                await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Lyrics update task exception: {e}")

    def _find_current_lyric_index(self, current_time: float) -> int:
        """
        Find the lyric index corresponding to the current time.
        """
        # Find the next line of lyrics
        next_lyric_index = None
        for i, (time_sec, _) in enumerate(self.lyrics):
            # Add a small offset (0.5 seconds) to make the lyric display more accurate
            if time_sec > current_time - 0.5:
                next_lyric_index = i
                break

        # Determine the current lyric index
        if next_lyric_index is not None and next_lyric_index > 0:
            # If the next line is found, the current line is the one before it
            return next_lyric_index - 1
        elif next_lyric_index is None and self.lyrics:
            # If the next line is not found, it means it's the last line
            return len(self.lyrics) - 1
        else:
            # Other cases (e.g., playback just started)
            return 0

    async def _display_current_lyric(self, current_index: int):
        """
        Display current lyric.
        """
        self.current_lyric_index = current_index

        if current_index < len(self.lyrics):
            time_sec, text = self.lyrics[current_index]

            # Add time and progress information before the lyric
            position_str = self._format_time(time.time() - self.start_play_time)
            duration_str = self._format_time(self.total_duration)
            display_text = f"[{position_str}/{duration_str}] {text}"

            # Update UI
            if self.app and hasattr(self.app, "set_chat_message"):
                await self._safe_update_ui(display_text)
                logger.debug(f"Displaying lyric: {text}")

    def _extract_value(self, text: str, start_marker: str, end_marker: str) -> str:
        """
        Extract value from text.
        """
        start_pos = text.find(start_marker)
        if start_pos == -1:
            return ""

        start_pos += len(start_marker)
        end_pos = text.find(end_marker, start_pos)

        if end_pos == -1:
            return ""

        return text[start_pos:end_pos]

    def _format_time(self, seconds: float) -> str:
        """
        Format seconds into mm:ss format.
        """
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"

    async def _safe_update_ui(self, message: str):
        """
        Safely update UI.
        """
        if not self.app or not hasattr(self.app, "set_chat_message"):
            return

        try:
            self.app.set_chat_message("assistant", message)
        except Exception as e:
            logger.error(f"Failed to update UI: {e}")

    def __del__(self):
        """
        Clean up resources.
        """
        try:
            # If the program exits normally, clean the temporary cache one more time
            self._clean_temp_cache()
        except Exception:
            # Ignore errors, as various exceptions can occur during object destruction
            pass
