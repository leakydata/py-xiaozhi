from abc import ABC, abstractmethod
from typing import Any, Dict, Type

from pydantic import BaseModel


class ToolBase(ABC):
    """
    Base class for tools.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the tool.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A description of the tool.
        """
        pass

    @property
    @abstractmethod
    def args_schema(self) -> Type[BaseModel]:
        """
        The Pydantic model for the tool's arguments.
        """
        pass

    @property
    @abstractmethod
    def results_schema(self) -> Type[BaseModel]:
        """
        The Pydantic model for the tool's results.
        """
        pass

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Runs the tool with the given arguments.
        """
        query = self.args_schema(**kwargs)
        result = await self._run(query)
        return result.dict()

    @abstractmethod
    async def _run(self, query: BaseModel) -> BaseModel:
        """
        The internal implementation of the tool's logic.
        """
        pass
