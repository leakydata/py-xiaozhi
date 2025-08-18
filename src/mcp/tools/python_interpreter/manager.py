from typing import Callable

from .tools import execute_python_code


class PythonInterpreterManager:
    def init_tools(self, add_tool: Callable, PropertyList, Property, PropertyType):
        properties = PropertyList(
            [
                Property("code", PropertyType.STRING),
            ]
        )
        add_tool(
            (
                "python_interpreter",
                "Executes Python code and returns the output.",
                properties,
                lambda args: execute_python_code(args["code"]),
            )
        )


_manager = PythonInterpreterManager()


def get_python_interpreter_manager():
    return _manager
