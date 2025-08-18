from typing import Callable

from .tools import read_webpage


class WebReaderManager:
    def init_tools(self, add_tool: Callable, PropertyList, Property, PropertyType):
        properties = PropertyList(
            [
                Property("url", PropertyType.STRING),
                Property(
                    "max_length",
                    PropertyType.INTEGER,
                    default_value=8000,
                    min_value=100,
                    max_value=16000,
                ),
            ]
        )

        async def web_reader_callback(args):
            return await read_webpage(args["url"], args.get("max_length", 8000))

        add_tool(
            (
                "web_reader",
                "Reads the content of a webpage from a URL.",
                properties,
                web_reader_callback,
            )
        )


_manager = WebReaderManager()


def get_web_reader_manager():
    return _manager
