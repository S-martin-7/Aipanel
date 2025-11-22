"""
Function calling / Tool use module for AIPanel.

Provides structured tool definitions and execution framework
for AI agents to interact with external systems.
"""

from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
import json
import inspect
from functools import wraps

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ToolParameterType(str, Enum):
    """JSON Schema types for tool parameters."""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: ToolParameterType
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None
    items: Optional[Dict] = None  # For array types


@dataclass
class ToolDefinition:
    """Definition of a callable tool."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None

    def to_openai_format(self) -> Dict:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.items:
                prop["items"] = param.items

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_anthropic_format(self) -> Dict:
        """Convert to Anthropic tool format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


@dataclass
class ToolCall:
    """Represents a tool call from the AI."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_call_id: str
    success: bool
    result: Any
    error: Optional[str] = None

    def to_message(self) -> Dict:
        """Convert to message format for AI."""
        if self.success:
            content = json.dumps(self.result) if not isinstance(self.result, str) else self.result
        else:
            content = f"Error: {self.error}"

        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": content,
        }


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def to_openai_format(self) -> List[Dict]:
        """Get all tools in OpenAI format."""
        return [tool.to_openai_format() for tool in self._tools.values()]

    def to_anthropic_format(self) -> List[Dict]:
        """Get all tools in Anthropic format."""
        return [tool.to_anthropic_format() for tool in self._tools.values()]


class ToolExecutor:
    """Executes tool calls from AI responses."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool = self.registry.get(tool_call.name)

        if not tool:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                result=None,
                error=f"Unknown tool: {tool_call.name}",
            )

        if not tool.handler:
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                result=None,
                error=f"No handler for tool: {tool_call.name}",
            )

        try:
            # Check if handler is async
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**tool_call.arguments)
            else:
                result = tool.handler(**tool_call.arguments)

            return ToolResult(
                tool_call_id=tool_call.id,
                success=True,
                result=result,
            )
        except Exception as e:
            logger.error(f"Tool execution error ({tool_call.name}): {e}")
            return ToolResult(
                tool_call_id=tool_call.id,
                success=False,
                result=None,
                error=str(e),
            )

    async def execute_all(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tool calls."""
        results = []
        for call in tool_calls:
            result = await self.execute(call)
            results.append(result)
        return results


def tool(
    name: str,
    description: str,
    parameters: List[ToolParameter] = None,
):
    """
    Decorator to register a function as a tool.

    Usage:
        @tool(
            name="get_weather",
            description="Get current weather for a location",
            parameters=[
                ToolParameter("location", ToolParameterType.STRING, "City name"),
            ]
        )
        async def get_weather(location: str) -> dict:
            # Implementation
            return {"temp": 20, "condition": "sunny"}
    """
    def decorator(func: Callable):
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters or [],
            handler=func,
        )

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)

        wrapper._tool_definition = tool_def
        return wrapper

    return decorator


# ============================================
# Built-in tools for AIPanel
# ============================================

# Search documents tool
search_documents_tool = ToolDefinition(
    name="search_documents",
    description="Search through uploaded documents to find relevant information",
    parameters=[
        ToolParameter(
            name="query",
            type=ToolParameterType.STRING,
            description="Search query to find relevant documents",
        ),
        ToolParameter(
            name="limit",
            type=ToolParameterType.INTEGER,
            description="Maximum number of results to return",
            required=False,
            default=5,
        ),
    ],
)

# Get current time tool
get_time_tool = ToolDefinition(
    name="get_current_time",
    description="Get the current date and time",
    parameters=[
        ToolParameter(
            name="timezone",
            type=ToolParameterType.STRING,
            description="Timezone (e.g., 'America/Santiago')",
            required=False,
            default="America/Santiago",
        ),
    ],
)

# Calculate tool
calculate_tool = ToolDefinition(
    name="calculate",
    description="Perform mathematical calculations",
    parameters=[
        ToolParameter(
            name="expression",
            type=ToolParameterType.STRING,
            description="Mathematical expression to evaluate (e.g., '2 + 2 * 3')",
        ),
    ],
)

# Web search tool (placeholder)
web_search_tool = ToolDefinition(
    name="web_search",
    description="Search the web for information",
    parameters=[
        ToolParameter(
            name="query",
            type=ToolParameterType.STRING,
            description="Search query",
        ),
        ToolParameter(
            name="num_results",
            type=ToolParameterType.INTEGER,
            description="Number of results to return",
            required=False,
            default=5,
        ),
    ],
)


# Create default registry with built-in tools
def create_default_registry() -> ToolRegistry:
    """Create a registry with default tools."""
    registry = ToolRegistry()
    registry.register(search_documents_tool)
    registry.register(get_time_tool)
    registry.register(calculate_tool)
    registry.register(web_search_tool)
    return registry


# Global default registry
default_tool_registry = create_default_registry()
