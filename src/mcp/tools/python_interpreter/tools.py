import io
import signal
import sys
import threading
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict

from .models import PythonInterpreterResult

# Modules that are not allowed to be imported in sandboxed execution
BLOCKED_MODULES = {
    "os", "subprocess", "shutil", "pathlib", "glob",
    "socket", "http", "urllib", "requests", "aiohttp",
    "ctypes", "importlib", "pickle", "shelve",
    "multiprocessing", "signal", "sys", "builtins",
    "__builtin__", "code", "codeop", "compile",
}

# Built-in functions that are blocked
BLOCKED_BUILTINS = {
    "exec", "eval", "compile", "__import__", "open",
    "input", "breakpoint", "exit", "quit",
}

MAX_EXECUTION_TIME = 10  # seconds
MAX_OUTPUT_LENGTH = 10000  # characters


ALLOWED_MODULES = {
    "math", "json", "datetime", "re", "random",
    "itertools", "functools", "collections", "statistics",
    "string", "textwrap", "decimal", "fractions",
}


def _create_safe_globals():
    """Create a restricted globals dict for safe code execution."""
    import builtins as _builtins
    import math
    import json
    import datetime
    import re
    import random
    import itertools
    import functools
    import collections
    import statistics

    # Build safe builtins from the builtins module directly
    safe_builtins = {}
    for name in dir(_builtins):
        if name not in BLOCKED_BUILTINS and not name.startswith("_"):
            safe_builtins[name] = getattr(_builtins, name)

    # Pre-import allowed modules so they're available
    allowed_module_objects = {
        "math": math,
        "json": json,
        "datetime": datetime,
        "re": re,
        "random": random,
        "itertools": itertools,
        "functools": functools,
        "collections": collections,
        "statistics": statistics,
    }

    # Provide a restricted __import__ that only allows safe modules
    def _safe_import(name, *args, **kwargs):
        if name in BLOCKED_MODULES:
            raise ImportError(f"Module '{name}' is not allowed in sandboxed execution")
        if name in allowed_module_objects:
            return allowed_module_objects[name]
        if name in ALLOWED_MODULES:
            import importlib
            return importlib.import_module(name)
        raise ImportError(f"Module '{name}' is not available in sandboxed execution")

    safe_builtins["__import__"] = _safe_import

    safe_globals = {"__builtins__": safe_builtins}
    safe_globals.update(allowed_module_objects)

    return safe_globals


def execute_python_code(code: str) -> Dict[str, Any]:
    """
    Executes Python code in a sandboxed environment with timeout protection.

    Restrictions:
    - No file system access (os, pathlib, shutil, glob blocked)
    - No network access (socket, http, requests blocked)
    - No process spawning (subprocess, multiprocessing blocked)
    - No dynamic code execution (exec, eval, compile blocked)
    - 10 second timeout
    - Output limited to 10000 characters
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None

    # Check for obviously dangerous patterns
    dangerous_patterns = [
        "import os", "import subprocess", "import shutil",
        "import socket", "import ctypes", "__import__",
        "import pathlib", "import signal",
    ]
    code_lower = code.lower().replace(" ", "")
    for pattern in dangerous_patterns:
        if pattern.replace(" ", "") in code_lower:
            return PythonInterpreterResult(
                stdout="",
                stderr=f"Security error: '{pattern}' is not allowed in sandboxed execution",
                result=None,
            ).dict()

    safe_globals = _create_safe_globals()
    local_vars = {}

    # Execute with timeout
    execution_error = [None]

    def target():
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals, local_vars)
        except Exception as e:
            execution_error[0] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=MAX_EXECUTION_TIME)

    if thread.is_alive():
        stderr_capture.write(f"Execution timed out after {MAX_EXECUTION_TIME} seconds")
    elif execution_error[0]:
        stderr_capture.write(str(execution_error[0]))

    if 'result' in local_vars:
        result = local_vars['result']

    stdout = stdout_capture.getvalue()[:MAX_OUTPUT_LENGTH]
    stderr = stderr_capture.getvalue()[:MAX_OUTPUT_LENGTH]

    if len(stdout_capture.getvalue()) > MAX_OUTPUT_LENGTH:
        stdout += f"\n... (output truncated at {MAX_OUTPUT_LENGTH} characters)"

    return PythonInterpreterResult(stdout=stdout, stderr=stderr, result=result).dict()
