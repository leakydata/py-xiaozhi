from pydantic import BaseModel, Field


class WebReaderQuery(BaseModel):
    """
    Web reader query model.
    """

    url: str = Field(..., description="The URL of the webpage to read.")
    max_length: int = Field(
        8000, ge=100, le=16000, description="The maximum length of the content to return."
    )


class WebReaderResult(BaseModel):
    """
    Web reader result model.
    """

    content: str = Field(..., description="The content of the webpage.")
