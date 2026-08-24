from typing import Dict, List, Any
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.tools.base import CommerceTool, ToolResult, ToolError

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, CommerceTool] = {}

    def register(self, tool: CommerceTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> CommerceTool:
        if name not in self._tools:
            raise ToolError("TOOL_NOT_FOUND", f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.get_metadata() for tool in self._tools.values()]

    def execute(self, name: str, input_data: Dict[str, Any], db_session: Session) -> ToolResult:
        try:
            tool = self.get(name)
        except ToolError as e:
            return ToolResult(
                success=False,
                tool=name,
                error={"code": e.code, "message": e.message}
            )

        try:
            # Validate input using the tool's schema
            validated_input = tool.input_schema(**input_data)
        except ValidationError as e:
            return ToolResult(
                success=False,
                tool=name,
                error={"code": "INVALID_INPUT", "message": str(e)}
            )

        try:
            # Execute tool logic
            result = tool.execute(db_session=db_session, **validated_input.model_dump())
            return ToolResult(
                success=True,
                tool=name,
                result=result
            )
        except ToolError as e:
            return ToolResult(
                success=False,
                tool=name,
                error={"code": e.code, "message": e.message}
            )
        except Exception as e:
            # Catch unexpected errors to prevent app crashes and hide internal traces
            return ToolResult(
                success=False,
                tool=name,
                error={"code": "INTERNAL_ERROR", "message": "An unexpected error occurred during tool execution."}
            )

registry = ToolRegistry()
