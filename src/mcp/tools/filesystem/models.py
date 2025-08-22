from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ReadFileQuery(BaseModel):
    """
    Query model for reading a file.
    """
    path: str = Field(..., description="The absolute path to the file to read.")

class ReadFileResult(BaseModel):
    """
    Result model for reading a file.
    """
    content: str = Field(..., description="The content of the file.")

class WriteFileQuery(BaseModel):
    """
    Query model for writing to a file.
    """
    path: str = Field(..., description="The absolute path to the file to write to.")
    content: str = Field(..., description="The content to write to the file.")

class WriteFileResult(BaseModel):
    """
    Result model for writing to a file.
    """
    message: str = Field(..., description="The result message.")

class RenameFileQuery(BaseModel):
    """
    Query model for renaming a file.
    """
    old_path: str = Field(..., description="The current absolute path of the file.")
    new_path: str = Field(..., description="The new absolute path for the file.")

class RenameFileResult(BaseModel):
    """
    Result model for renaming a file.
    """
    message: str = Field(..., description="The result message.")

class ListDirectoryQuery(BaseModel):
    """
    Query model for listing a directory's contents.
    """
    path: str = Field(..., description="The absolute path of the directory to list.")

class ListDirectoryResult(BaseModel):
    """
    Result model for listing a directory's contents.
    """
    contents: List[str] = Field(..., description="The list of files and directories.")

class GetFileInfoQuery(BaseModel):
    """
    Query model for getting file information.
    """
    path: str = Field(..., description="The absolute path of the file or directory.")

class GetFileInfoResult(BaseModel):
    """
    Result model for getting file information.
    """
    info: Dict[str, Any] = Field(..., description="A dictionary containing file information.")
