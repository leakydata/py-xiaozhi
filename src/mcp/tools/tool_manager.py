from typing import Dict, Type

from .calendar.calendar_tool import CalendarTool
from .camera.camera_tool import CameraTool
from .music.music_tool import MusicTool
from .railway.railway_tool import RailwayTool
from .recipe.recipe_tool import RecipeTool
from .search.search_tool import SearchTool
from .system.system_tool import SystemTool
from .timer.timer_tool import TimerTool
from .tool_base import ToolBase
from .web_reader.web_reader_tool import WebReaderTool


class ToolManager:
    def __init__(self):
        self._tools: Dict[str, ToolBase] = {}
        self._register_all_tools()

    def _register_tool(self, tool_class: Type[ToolBase]):
        tool = tool_class()
        self._tools[tool.name] = tool

    def _register_all_tools(self):
        self._register_tool(CalendarTool)
        self._register_tool(CameraTool)
        self._register_tool(MusicTool)
        self._register_tool(RailwayTool)
        self._register_tool(RecipeTool)
        self._register_tool(SearchTool)
        self._register_tool(SystemTool)
        self._register_tool(TimerTool)
        self._register_tool(WebReaderTool)

    def get_tool(self, name: str) -> ToolBase:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found.")
        return self._tools[name]

    def get_all_tools(self):
        return self._tools.values()


tool_manager = ToolManager()
