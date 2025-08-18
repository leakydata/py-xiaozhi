import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict

from .models import PythonInterpreterResult


def execute_python_code(code: str) -> Dict[str, Any]:
    """
    Executes Python code and captures its output.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = None
    
    local_vars = {}

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, globals(), local_vars)
        
        # Potentially look for a 'result' variable in local_vars if a convention is established
        if 'result' in local_vars:
            result = local_vars['result']

    except Exception as e:
        stderr_capture.write(str(e))

    stdout = stdout_capture.getvalue()
    stderr = stderr_capture.getvalue()

    return PythonInterpreterResult(stdout=stdout, stderr=stderr, result=result).dict()
