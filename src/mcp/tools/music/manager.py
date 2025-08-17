"""Music tool manager.

Responsible for music tool initialization, configuration, and MCP tool registration.
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .music_player import get_music_player_instance

logger = get_logger(__name__)


class MusicToolsManager:
    """
    Music tool manager.
    """

    def __init__(self):
        """
        Initialize the music tool manager.
        """
        self._initialized = False
        self._music_player = None
        logger.info("[MusicManager] Music tool manager initialized")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initialize and register all music tools.
        """
        try:
            logger.info("[MusicManager] Starting to register music tools")

            # Get the music player singleton instance
            self._music_player = get_music_player_instance()

            # Register search and play tool
            self._register_search_and_play_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register play/pause tool
            self._register_play_pause_tool(add_tool, PropertyList)

            # Register stop tool
            self._register_stop_tool(add_tool, PropertyList)

            # Register seek tool
            self._register_seek_tool(add_tool, PropertyList, Property, PropertyType)

            # Register get lyrics tool
            self._register_get_lyrics_tool(add_tool, PropertyList)

            # Register get status tool
            self._register_get_status_tool(add_tool, PropertyList)

            # Register get local playlist tool
            self._register_get_local_playlist_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            self._initialized = True
            logger.info("[MusicManager] Music tool registration complete")

        except Exception as e:
            logger.error(f"[MusicManager] Music tool registration failed: {e}", exc_info=True)
            raise

    def _register_search_and_play_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register the search and play tool.
        """

        async def search_and_play_wrapper(args: Dict[str, Any]) -> str:
            song_name = args.get("song_name", "")
            result = await self._music_player.search_and_play(song_name)
            return result.get("message", "Search and play complete")

        search_props = PropertyList([Property("song_name", PropertyType.STRING)])

        add_tool(
            (
                "music_player.search_and_play",
                "Search for a song and start playing it. Finds songs by name and "
                "automatically starts playback. Use this to play specific songs "
                "requested by the user.",
                search_props,
                search_and_play_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered search and play tool successfully")

    def _register_play_pause_tool(self, add_tool, PropertyList):
        """
        Register the play/pause tool.
        """

        async def play_pause_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.play_pause()
            return result.get("message", "Playback state toggled successfully")

        add_tool(
            (
                "music_player.play_pause",
                "Toggle between play and pause states. If music is playing, it will "
                "pause. If music is paused or stopped, it will resume or start playing. "
                "Use this when user wants to pause/resume music.",
                PropertyList(),
                play_pause_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered play/pause tool successfully")

    def _register_stop_tool(self, add_tool, PropertyList):
        """
        Register the stop tool.
        """

        async def stop_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.stop()
            return result.get("message", "Playback stopped successfully")

        add_tool(
            (
                "music_player.stop",
                "Stop music playback completely. This will stop the current song "
                "and reset the position to the beginning. Use this when user wants "
                "to stop music completely.",
                PropertyList(),
                stop_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered stop tool successfully")

    def _register_seek_tool(self, add_tool, PropertyList, Property, PropertyType):
        """
        Register the seek tool.
        """

        async def seek_wrapper(args: Dict[str, Any]) -> str:
            position = args.get("position", 0)
            result = await self._music_player.seek(float(position))
            return result.get("message", "Seek complete")

        seek_props = PropertyList(
            [Property("position", PropertyType.INTEGER, min_value=0)]
        )

        add_tool(
            (
                "music_player.seek",
                "Jump to a specific position in the currently playing song. "
                "Position is specified in seconds from the beginning. Use this "
                "when user wants to skip to a specific part of a song.",
                seek_props,
                seek_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered seek tool successfully")

    def _register_get_lyrics_tool(self, add_tool, PropertyList):
        """
        Register the get lyrics tool.
        """

        async def get_lyrics_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.get_lyrics()
            if result.get("status") == "success":
                lyrics = result.get("lyrics", [])
                return "Lyrics:\n" + "\n".join(lyrics)
            else:
                return result.get("message", "Failed to get lyrics")

        add_tool(
            (
                "music_player.get_lyrics",
                "Get the lyrics of the currently playing song. Returns the complete "
                "lyrics with timestamps. Use this when user asks for lyrics or wants "
                "to see the words of the current song.",
                PropertyList(),
                get_lyrics_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered get lyrics tool successfully")

    def _register_get_status_tool(self, add_tool, PropertyList):
        """
        Register the get status tool.
        """

        async def get_status_wrapper(args: Dict[str, Any]) -> str:
            result = await self._music_player.get_status()
            if result.get("status") == "success":
                status_info = []
                status_info.append(f"Current song: {result.get('current_song', 'None')}")
                status_info.append(
                    f"Playback status: {'Playing' if result.get('is_playing') else 'Stopped'}"
                )
                if result.get("is_playing"):
                    if result.get("paused"):
                        status_info.append("State: Paused")
                    else:
                        status_info.append("State: Playing")

                    duration = result.get("duration", 0)
                    position = result.get("position", 0)
                    progress = result.get("progress", 0)

                    status_info.append(f"Duration: {self._format_time(duration)}")
                    status_info.append(f"Current position: {self._format_time(position)}")
                    status_info.append(f"Playback progress: {progress}%")
                    has_lyrics = "Yes" if result.get("has_lyrics") else "No"
                    status_info.append(f"Lyrics available: {has_lyrics}")

                return "\n".join(status_info)
            else:
                return "Failed to get player status"

        add_tool(
            (
                "music_player.get_status",
                "Get the current status of the music player including current song, "
                "play state, position, duration, and progress. Use this to check "
                "what's currently playing or get detailed playback information.",
                PropertyList(),
                get_status_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered get status tool successfully")

    def _register_get_local_playlist_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register the get local playlist tool.
        """

        async def get_local_playlist_wrapper(args: Dict[str, Any]) -> str:
            force_refresh = args.get("force_refresh", False)
            result = await self._music_player.get_local_playlist(force_refresh)

            if result.get("status") == "success":
                playlist = result.get("playlist", [])
                total_count = result.get("total_count", 0)

                if playlist:
                    playlist_text = f"Local music playlist (Total {total_count} songs):\n"
                    playlist_text += "\n".join(playlist)
                    return playlist_text
                else:
                    return "No music files in local cache"
            else:
                return result.get("message", "Failed to get local playlist")

        refresh_props = PropertyList(
            [Property("force_refresh", PropertyType.BOOLEAN, default_value=False)]
        )

        add_tool(
            (
                "music_player.get_local_playlist",
                "Get the local music playlist from cache. Shows all songs that have been "
                "downloaded and cached locally. Returns songs in format 'Title - Artist'. "
                "To play a song from this list, use search_and_play with just the song title "
                "(not the full 'Title - Artist' format). For example: if the list shows "
                "'菊花台 - 周杰伦', call search_and_play with song_name='菊花台'.",
                refresh_props,
                get_local_playlist_wrapper,
            )
        )
        logger.debug("[MusicManager] Registered get local playlist tool successfully")

    def _format_time(self, seconds: float) -> str:
        """
        Format seconds to mm:ss format.
        """
        minutes = int(seconds) // 60
        seconds = int(seconds) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def is_initialized(self) -> bool:
        """
        Check if the manager is initialized.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Get the manager status.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 7,  # Number of currently registered tools
            "available_tools": [
                "search_and_play",
                "play_pause",
                "stop",
                "seek",
                "get_lyrics",
                "get_status",
                "get_local_playlist",
            ],
            "music_player_ready": self._music_player is not None,
        }


# Global manager instance
_music_tools_manager = None


def get_music_tools_manager() -> MusicToolsManager:
    """
    Get the music tool manager singleton.
    """
    global _music_tools_manager
    if _music_tools_manager is None:
        _music_tools_manager = MusicToolsManager()
        logger.debug("[MusicManager] Created music tool manager instance")
    return _music_tools_manager
