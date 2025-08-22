from typing import Callable

from .tools import (
    read_file,
    write_file,
    rename_file,
    list_directory,
    get_file_info,
)


class FilesystemManager:
    def init_tools(self, add_tool: Callable, PropertyList, Property, PropertyType):
        # Read File Tool
        read_properties = PropertyList([Property("path", PropertyType.STRING)])
        async def read_file_callback(args):
            return await read_file(args["path"])
        add_tool(
            (
                "filesystem_read_file",
                "Reads the content of a file from a given path.",
                read_properties,
                read_file_callback,
            )
        )

        # Write File Tool
        write_properties = PropertyList(
            [
                Property("path", PropertyType.STRING),
                Property("content", PropertyType.STRING),
            ]
        )
        async def write_file_callback(args):
            return await write_file(args["path"], args["content"])
        add_tool(
            (
                "filesystem_write_file",
                "Writes content to a file at a given path. Creates the file if it does not exist.",
                write_properties,
                write_file_callback,
            )
        )

        # Rename File Tool
        rename_properties = PropertyList(
            [
                Property("old_path", PropertyType.STRING),
                Property("new_path", PropertyType.STRING),
            ]
        )
        async def rename_file_callback(args):
            return await rename_file(args["old_path"], args["new_path"])
        add_tool(
            (
                "filesystem_rename_file",
                "Renames or moves a file.",
                rename_properties,
                rename_file_callback,
            )
        )

        # List Directory Tool
        list_dir_properties = PropertyList([Property("path", PropertyType.STRING)])
        async def list_directory_callback(args):
            return await list_directory(args["path"])
        add_tool(
            (
                "filesystem_list_directory",
                "Lists the contents of a directory.",
                list_dir_properties,
                list_directory_callback,
            )
        )

        # Get File Info Tool
        get_info_properties = PropertyList([Property("path", PropertyType.STRING)])
        async def get_file_info_callback(args):
            return await get_file_info(args["path"])
        add_tool(
            (
                "filesystem_get_file_info",
                "Gets information about a file or directory.",
                get_info_properties,
                get_file_info_callback,
            )
        )


_manager = FilesystemManager()


def get_filesystem_manager():
    return _manager
