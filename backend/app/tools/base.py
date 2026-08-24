from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

class ToolError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)

class ToolResult(BaseModel):
    success: bool
    tool: str
    result: Optional[Any] = None
    error: Optional[Dict[str, str]] = None

class CommerceTool(ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    read_only: bool = True

    @abstractmethod
    def execute(self, db_session, **kwargs) -> Any:
        pass

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
            "read_only": self.read_only
        }
