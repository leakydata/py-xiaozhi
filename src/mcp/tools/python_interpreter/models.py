from pydantic import BaseModel, Field
from typing import Any, Optional


class PythonInterpreterQuery(BaseModel):
    """
    Python interpreter query model.
    """

    code: str = Field(..., description="The Python code to execute.")


class PythonInterpreterResult(BaseModel):
    """
    Python interpreter result model.
    """

    stdout: Optional[str] = Field(None, description="The standard output of the executed code.")
    stderr: Optional[str] = Field(None, description="The standard error of the executed code.")
    result: Optional[Any] = Field(None, description="The result of the executed code, if any.")
