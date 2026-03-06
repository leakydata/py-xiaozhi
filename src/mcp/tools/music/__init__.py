"""Music player toolkit.

Provides complete music playback functionality, including search, play, pause, stop, seek, and more.
"""

from .manager import MusicToolsManager, get_music_tools_manager
from .music_player import get_music_player_instance

__all__ = [
    "MusicToolsManager",
    "get_music_tools_manager",
    "get_music_player_instance",
]
