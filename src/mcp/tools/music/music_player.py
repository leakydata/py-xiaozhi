"""Music player singleton implementation.

Provides a singleton music player, initialized on registration, supporting asynchronous operations.
"""

import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

import pygame
import requests

from src.constants.constants import AudioConfig
from src.utils.logging_config import get_logger
from src.utils.resource_finder import get_project_root

# Try to import music metadata database
try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3NoHeaderError

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

logger = get_logger(__name__)


class MusicMetadata:
    """
    Music metadata class.
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.filename = file_path.name
        self.file_id = file_path.stem  # Filename without extension, i.e., song ID
        self.file_size = file_path.stat().st_size

        # Metadata extracted from the file
        self.title = None
        self.artist = None
        self.album = None
        self.duration = None  # in seconds

    def extract_metadata(self) -> bool:
        """
        Extract music file metadata.
        """
        if not MUTAGEN_AVAILABLE:
            return False

        try:
            audio_file = MutagenFile(self.file_path)
            if audio_file is None:
                return False

            # Basic information
            if hasattr(audio_file, "info"):
                self.duration = getattr(audio_file.info, "length", None)

            # ID3 tag information
            tags = audio_file.tags if audio_file.tags else {}

            # Title
            self.title = self._get_tag_value(tags, ["TIT2", "TITLE", "\xa9nam"])

            # Artist
            self.artist = self._get_tag_value(tags, ["TPE1", "ARTIST", "\xa9ART"])

            # Album
            self.album = self._get_tag_value(tags, ["TALB", "ALBUM", "\xa9alb"])

            return True

        except ID3NoHeaderError:
            # No ID3 tag, not an error
            return True
        except Exception as e:
            logger.debug(f"Failed to extract metadata {self.filename}: {e}")
            return False

    def _get_tag_value(self, tags: dict, tag_names: List[str]) -> Optional[str]:
        """
        Get value from multiple possible tag names.
        """
        for tag_name in tag_names:
            if tag_name in tags:
                value = tags[tag_name]
                if isinstance(value, list) and value:
                    return str(value[0])
                elif value:
                    return str(value)
        return None

    def format_duration(self) -> str:
        """
        Format playback duration.
        """
        if self.duration is None:
            return "Unknown"

        minutes = int(self.duration) // 60
        seconds = int(self.duration) % 60
        return f"{minutes:02d}:{seconds:02d}"


class MusicPlayer:
    """Music Player - Designed for IoT devices

    Retains only core functions: search, play, pause, stop, seek
    """

    def __init__(self):
        # Initialize pygame mixer
        pygame.mixer.init(
            frequency=AudioConfig.OUTPUT_SAMPLE_RATE, channels=AudioConfig.CHANNELS
        )

        # Core playback status
        self.current_song = ""
        self.current_url = ""
        self.song_id = ""
        self.total_duration = 0
        self.is_playing = False
        self.paused = False
        self.current_position = 0
        self.start_play_time = 0

        # Lyrics related
        self.lyrics = []  # Lyrics list, format: [(time, text), ...]
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

        # Clean up temporary cache
        self._clean_temp_cache()

        # Get application instance
        self.app = None
        self._initialize_app_reference()

        # Local playlist cache
        self._local_playlist = None
        self._last_scan_time = 0

        logger.info("Music player singleton initialization complete")

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
            # Fallback to system temporary directory
            self.cache_dir = Path(tempfile.gettempdir()) / "xiaozhi_music_cache"
            self.temp_cache_dir = self.cache_dir / "temp"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.temp_cache_dir.mkdir(parents=True, exist_ok=True)

    def _clean_temp_cache(self):
        """
        Clean up temporary cache files.
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
            logger.error(f"Failed to clean up temporary cache directory: {e}")

    def _scan_local_music(self, force_refresh: bool = False) -> List[MusicMetadata]:
        """
        Scan local music cache and return a playlist.
        """
        current_time = time.time()

        # If not forcing refresh and cache is not expired (5 minutes), return cache directly
        if (
            not force_refresh
            and self._local_playlist is not None
            and (current_time - self._last_scan_time) < 300
        ):
            return self._local_playlist

        playlist = []

        if not self.cache_dir.exists():
            logger.warning(f"Cache directory does not exist: {self.cache_dir}")
            return playlist

        # Find all music files
        music_files = []
        for pattern in ["*.mp3", "*.m4a", "*.flac", "*.wav", "*.ogg"]:
            music_files.extend(self.cache_dir.glob(pattern))

        logger.debug(f"Found {len(music_files)} music files")

        # Scan each file
        for file_path in music_files:
            try:
                metadata = MusicMetadata(file_path)

                # Try to extract metadata
                if MUTAGEN_AVAILABLE:
                    metadata.extract_metadata()

                playlist.append(metadata)

            except Exception as e:
                logger.debug(f"Failed to process music file {file_path.name}: {e}")

        # Sort by artist and title
        playlist.sort(key=lambda x: (x.artist or "Unknown", x.title or x.filename))

        # Update cache
        self._local_playlist = playlist
        self._last_scan_time = current_time

        logger.info(f"Scan complete, found {len(playlist)} local songs")
        return playlist

    async def get_local_playlist(self, force_refresh: bool = False) -> dict:
        """
        Get local music playlist.
        """
        try:
            playlist = self._scan_local_music(force_refresh)

            if not playlist:
                return {
                    "status": "info",
                    "message": "No music files in local cache",
                    "playlist": [],
                    "total_count": 0,
                }

            # Format playlist in a simple format for AI to read
            formatted_playlist = []
            for metadata in playlist:
                title = metadata.title or "Unknown Title"
                artist = metadata.artist or "Unknown Artist"
                song_info = f"{title} - {artist}"
                formatted_playlist.append(song_info)

            return {
                "status": "success",
                "message": f"Found {len(playlist)} local songs",
                "playlist": formatted_playlist,
                "total_count": len(playlist),
            }

        except Exception as e:
            logger.error(f"Failed to get local playlist: {e}")
            return {
                "status": "error",
                "message": f"Failed to get local playlist: {str(e)}",
                "playlist": [],
                "total_count": 0,
            }

    async def search_local_music(self, query: str) -> dict:
        """
        Search local music.
        """
        try:
            playlist = self._scan_local_music()

            if not playlist:
                return {
                    "status": "info",
                    "message": "No music files in local cache",
                    "results": [],
                    "found_count": 0,
                }

            query = query.lower()
            results = []

            for metadata in playlist:
                # Search in title, artist, filename
                searchable_text = " ".join(
                    filter(
                        None,
                        [
                            metadata.title,
                            metadata.artist,
                            metadata.album,
                            metadata.filename,
                        ],
                    )
                ).lower()

                if query in searchable_text:
                    title = metadata.title or "Unknown Title"
                    artist = metadata.artist or "Unknown Artist"
                    song_info = f"{title} - {artist}"
                    results.append(
                        {
                            "song_info": song_info,
                            "file_id": metadata.file_id,
                            "duration": metadata.format_duration(),
                        }
                    )

            return {
                "status": "success",
                "message": f"Found {len(results)} matching songs in local music",
                "results": results,
                "found_count": len(results),
            }

        except Exception as e:
            logger.error(f"Failed to search local music: {e}")
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}",
                "results": [],
                "found_count": 0,
            }

    async def play_local_song_by_id(self, file_id: str) -> dict:
        """
        Play local song by file ID.
        """
        try:
            # Build file path
            file_path = self.cache_dir / f"{file_id}.mp3"

            if not file_path.exists():
                # Try other formats
                for ext in [".m4a", ".flac", ".wav", ".ogg"]:
                    alt_path = self.cache_dir / f"{file_id}{ext}"
                    if alt_path.exists():
                        file_path = alt_path
                        break
                else:
                    return {"status": "error", "message": f"Local file does not exist: {file_id}"}

            # Get song information
            metadata = MusicMetadata(file_path)
            if MUTAGEN_AVAILABLE:
                metadata.extract_metadata()

            # Stop current playback
            if self.is_playing:
                pygame.mixer.music.stop()

            # Load and play
            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.play()

            # Update playback status
            title = metadata.title or "Unknown Title"
            artist = metadata.artist or "Unknown Artist"
            self.current_song = f"{title} - {artist}"
            self.song_id = file_id
            self.total_duration = metadata.duration or 0
            self.current_url = str(file_path)  # Local file path
            self.is_playing = True
            self.paused = False
            self.current_position = 0
            self.start_play_time = time.time()
            self.current_lyric_index = -1
            self.lyrics = []  # Lyrics not supported for local files yet

            logger.info(f"Start playing local music: {self.current_song}")

            # Update UI
            if self.app and hasattr(self.app, "set_chat_message"):
                await self._safe_update_ui(f"Playing local music: {self.current_song}")

            return {
                "status": "success",
                "message": f"Playing local music: {self.current_song}",
            }

        except Exception as e:
            logger.error(f"Failed to play local music: {e}")
            return {"status": "error", "message": f"Playback failed: {str(e)}"}

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
        Handle playback completion.
        """
        if self.is_playing:
            logger.info(f"Song playback complete: {self.current_song}")
            pygame.mixer.music.stop()
            self.is_playing = False
            self.paused = False
            self.current_position = self.total_duration

            # Update UI to show completion status
            if self.app and hasattr(self.app, "set_chat_message"):
                dur_str = self._format_time(self.total_duration)
                await self._safe_update_ui(f"Playback complete: {self.current_song} [{dur_str}]")

    # Core methods
    async def search_and_play(self, song_name: str) -> dict:
        """
        Search and play a song.
        """
        try:
            # Search for the song
            song_id, url = await self._search_song(song_name)
            if not song_id or not url:
                return {"status": "error", "message": f"Song not found: {song_name}"}

            # Play the song
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

    async def play_pause(self) -> dict:
        """
        Toggle play/pause.
        """
        try:
            if not self.is_playing and self.current_url:
                # Replay
                success = await self._play_url(self.current_url)
                return {
                    "status": "success" if success else "error",
                    "message": (
                        f"Start playing: {self.current_song}" if success else "Playback failed"
                    ),
                }

            elif self.is_playing and self.paused:
                # Resume playback
                pygame.mixer.music.unpause()
                self.paused = False
                self.start_play_time = time.time() - self.current_position

                # Update UI
                if self.app and hasattr(self.app, "set_chat_message"):
                    await self._safe_update_ui(f"Resuming: {self.current_song}")

                return {
                    "status": "success",
                    "message": f"Resuming: {self.current_song}",
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

    async def stop(self) -> dict:
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

    async def seek(self, position: float) -> dict:
        """
        Seek to a specific position.
        """
        try:
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

    async def get_lyrics(self) -> dict:
        """
        Get lyrics for the current song.
        """
        if not self.lyrics:
            return {"status": "info", "message": "No lyrics for the current song", "lyrics": []}

        # Extract lyric text and convert to a list
        lyrics_text = []
        for time_sec, text in self.lyrics:
            time_str = self._format_time(time_sec)
            lyrics_text.append(f"[{time_str}] {text}")

        return {
            "status": "success",
            "message": f"Got {len(self.lyrics)} lines of lyrics",
            "lyrics": lyrics_text,
        }

    async def get_status(self) -> dict:
        """
        Get player status.
        """
        position = await self.get_position()
        progress = await self.get_progress()

        return {
            "status": "success",
            "current_song": self.current_song,
            "is_playing": self.is_playing,
            "paused": self.paused,
            "duration": self.total_duration,
            "position": position,
            "progress": progress,
            "has_lyrics": len(self.lyrics) > 0,
        }

    # Internal methods
    async def _search_song(self, song_name: str) -> Tuple[str, str]:
        """
        Search for a song to get its ID and URL.
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

            # Search for the song
            response = await asyncio.to_thread(
                requests.get,
                self.config["SEARCH_URL"],
                params=params,
                headers=self.config["HEADERS"],
                timeout=10,
            )
            response.raise_for_status()

            # Parse the response
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
                # Get lyrics
                await self._fetch_lyrics(song_id)
                return song_id, play_url_text

            return song_id, ""

        except Exception as e:
            logger.error(f"Failed to search for song: {e}")
            return "", ""

    async def _play_url(self, url: str) -> bool:
        """
        Play the specified URL.
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

            logger.info(f"Start playing: {self.current_song}")

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
        """Get or download a file.

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

            # Cache does not exist, download is required
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
                logger.warning(f"Did not get lyrics or lyrics format is incorrect: {data.get('msg', '')}")

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
            # If the next line is found, the current lyric is the one before it
            return next_lyric_index - 1
        elif next_lyric_index is None and self.lyrics:
            # If the next line is not found, it means it's the last line
            return len(self.lyrics) - 1
        else:
            # Other cases (e.g., playback just started)
            return 0

    async def _display_current_lyric(self, current_index: int):
        """
        Display the current lyric.
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
        Extract a value from text.
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
        Safely update the UI.
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
            if pygame.mixer.get_init():
                pygame.mixer.quit()
                logger.info("Pygame mixer quit successfully")
        except Exception as e:
            logger.error(f"Error quitting pygame mixer: {e}")


# Global player instance
_music_player_instance = None


def get_music_player_instance() -> "MusicPlayer":
    """
    Get the music player singleton.
    """
    global _music_player_instance
    if _music_player_instance is None:
        _music_player_instance = MusicPlayer()
        logger.debug("Created music player instance")
    return _music_player_instance
