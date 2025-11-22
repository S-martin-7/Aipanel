"""
Tests for function calling / tools module.
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4


class TestToolDefinition:
    """Test tool definition and formatting."""

    def test_tool_definition_creation(self):
        """Test creating a tool definition."""
        from app.integrations.tools import (
            ToolDefinition,
            ToolParameter,
            ToolParameterType,
        )

        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="limit",
                    type=ToolParameterType.INTEGER,
                    description="Result limit",
                    required=False,
                    default=10,
                ),
            ],
        )

        assert tool.name == "test_tool"
        assert len(tool.parameters) == 2

    def test_openai_format(self):
        """Test conversion to OpenAI function calling format."""
        from app.integrations.tools import (
            ToolDefinition,
            ToolParameter,
            ToolParameterType,
        )

        tool = ToolDefinition(
            name="get_weather",
            description="Get weather for a location",
            parameters=[
                ToolParameter(
                    name="location",
                    type=ToolParameterType.STRING,
                    description="City name",
                    required=True,
                ),
                ToolParameter(
                    name="units",
                    type=ToolParameterType.STRING,
                    description="Temperature units",
                    required=False,
                    enum=["celsius", "fahrenheit"],
                ),
            ],
        )

        openai_format = tool.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "get_weather"
        assert "parameters" in openai_format["function"]
        assert openai_format["function"]["parameters"]["type"] == "object"
        assert "location" in openai_format["function"]["parameters"]["properties"]
        assert "units" in openai_format["function"]["parameters"]["properties"]
        assert openai_format["function"]["parameters"]["properties"]["units"]["enum"] == [
            "celsius",
            "fahrenheit",
        ]

    def test_anthropic_format(self):
        """Test conversion to Anthropic tool format."""
        from app.integrations.tools import (
            ToolDefinition,
            ToolParameter,
            ToolParameterType,
        )

        tool = ToolDefinition(
            name="search_documents",
            description="Search through documents",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ToolParameterType.STRING,
                    description="Search query",
                    required=True,
                ),
            ],
        )

        anthropic_format = tool.to_anthropic_format()

        assert anthropic_format["name"] == "search_documents"
        assert "input_schema" in anthropic_format
        assert anthropic_format["input_schema"]["type"] == "object"
        assert "query" in anthropic_format["input_schema"]["properties"]


class TestToolRegistry:
    """Test tool registry functionality."""

    def test_register_tool(self):
        """Test registering a tool."""
        from app.integrations.tools import ToolRegistry, ToolDefinition

        registry = ToolRegistry()
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
        )

        registry.register(tool)

        assert registry.get("test_tool") is not None
        assert registry.get("test_tool").name == "test_tool"

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        from app.integrations.tools import ToolRegistry, ToolDefinition

        registry = ToolRegistry()
        tool = ToolDefinition(name="test_tool", description="Test")

        registry.register(tool)
        assert registry.get("test_tool") is not None

        registry.unregister("test_tool")
        assert registry.get("test_tool") is None

    def test_list_tools(self):
        """Test listing all tools."""
        from app.integrations.tools import ToolRegistry, ToolDefinition

        registry = ToolRegistry()
        registry.register(ToolDefinition(name="tool1", description="Tool 1"))
        registry.register(ToolDefinition(name="tool2", description="Tool 2"))

        tools = registry.list_tools()

        assert len(tools) == 2
        names = [t.name for t in tools]
        assert "tool1" in names
        assert "tool2" in names

    def test_to_openai_format_all(self):
        """Test converting all tools to OpenAI format."""
        from app.integrations.tools import ToolRegistry, ToolDefinition

        registry = ToolRegistry()
        registry.register(ToolDefinition(name="tool1", description="Tool 1"))
        registry.register(ToolDefinition(name="tool2", description="Tool 2"))

        openai_tools = registry.to_openai_format()

        assert len(openai_tools) == 2
        assert all(t["type"] == "function" for t in openai_tools)

    def test_to_anthropic_format_all(self):
        """Test converting all tools to Anthropic format."""
        from app.integrations.tools import ToolRegistry, ToolDefinition

        registry = ToolRegistry()
        registry.register(ToolDefinition(name="tool1", description="Tool 1"))
        registry.register(ToolDefinition(name="tool2", description="Tool 2"))

        anthropic_tools = registry.to_anthropic_format()

        assert len(anthropic_tools) == 2
        assert all("input_schema" in t for t in anthropic_tools)


class TestToolExecutor:
    """Test tool executor functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        from app.integrations.tools import (
            ToolRegistry,
            ToolDefinition,
            ToolExecutor,
            ToolCall,
        )

        async def mock_handler(query: str) -> dict:
            return {"result": f"Found: {query}"}

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="search",
                description="Search",
                handler=mock_handler,
            )
        )

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_123",
            name="search",
            arguments={"query": "test"},
        )

        result = await executor.execute(tool_call)

        assert result.success is True
        assert result.result["result"] == "Found: test"
        assert result.tool_call_id == "call_123"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test executing an unknown tool."""
        from app.integrations.tools import ToolRegistry, ToolExecutor, ToolCall

        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        tool_call = ToolCall(
            id="call_123",
            name="unknown_tool",
            arguments={},
        )

        result = await executor.execute(tool_call)

        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_execute_tool_no_handler(self):
        """Test executing tool without handler."""
        from app.integrations.tools import (
            ToolRegistry,
            ToolDefinition,
            ToolExecutor,
            ToolCall,
        )

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="no_handler_tool",
                description="Tool without handler",
                handler=None,
            )
        )

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_123",
            name="no_handler_tool",
            arguments={},
        )

        result = await executor.execute(tool_call)

        assert result.success is False
        assert "No handler" in result.error

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self):
        """Test tool execution with exception."""
        from app.integrations.tools import (
            ToolRegistry,
            ToolDefinition,
            ToolExecutor,
            ToolCall,
        )

        async def failing_handler():
            raise ValueError("Something went wrong")

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="failing_tool",
                description="A failing tool",
                handler=failing_handler,
            )
        )

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_123",
            name="failing_tool",
            arguments={},
        )

        result = await executor.execute(tool_call)

        assert result.success is False
        assert "Something went wrong" in result.error

    @pytest.mark.asyncio
    async def test_execute_sync_handler(self):
        """Test executing a synchronous handler."""
        from app.integrations.tools import (
            ToolRegistry,
            ToolDefinition,
            ToolExecutor,
            ToolCall,
        )

        def sync_handler(x: int) -> dict:
            return {"doubled": x * 2}

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="double",
                description="Double a number",
                handler=sync_handler,
            )
        )

        executor = ToolExecutor(registry)
        tool_call = ToolCall(
            id="call_123",
            name="double",
            arguments={"x": 5},
        )

        result = await executor.execute(tool_call)

        assert result.success is True
        assert result.result["doubled"] == 10

    @pytest.mark.asyncio
    async def test_execute_all(self):
        """Test executing multiple tool calls."""
        from app.integrations.tools import (
            ToolRegistry,
            ToolDefinition,
            ToolExecutor,
            ToolCall,
        )

        async def add_handler(a: int, b: int) -> dict:
            return {"sum": a + b}

        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="add",
                description="Add numbers",
                handler=add_handler,
            )
        )

        executor = ToolExecutor(registry)
        tool_calls = [
            ToolCall(id="call_1", name="add", arguments={"a": 1, "b": 2}),
            ToolCall(id="call_2", name="add", arguments={"a": 3, "b": 4}),
        ]

        results = await executor.execute_all(tool_calls)

        assert len(results) == 2
        assert results[0].result["sum"] == 3
        assert results[1].result["sum"] == 7


class TestToolResult:
    """Test tool result handling."""

    def test_success_result_to_message(self):
        """Test converting success result to message."""
        from app.integrations.tools import ToolResult

        result = ToolResult(
            tool_call_id="call_123",
            success=True,
            result={"data": "test"},
        )

        message = result.to_message()

        assert message["role"] == "tool"
        assert message["tool_call_id"] == "call_123"
        assert '"data": "test"' in message["content"]

    def test_error_result_to_message(self):
        """Test converting error result to message."""
        from app.integrations.tools import ToolResult

        result = ToolResult(
            tool_call_id="call_123",
            success=False,
            result=None,
            error="Something went wrong",
        )

        message = result.to_message()

        assert message["role"] == "tool"
        assert "Error:" in message["content"]
        assert "Something went wrong" in message["content"]


class TestToolDecorator:
    """Test tool decorator functionality."""

    @pytest.mark.asyncio
    async def test_tool_decorator(self):
        """Test the @tool decorator."""
        from app.integrations.tools import tool, ToolParameter, ToolParameterType

        @tool(
            name="calculate",
            description="Perform calculation",
            parameters=[
                ToolParameter(
                    name="expression",
                    type=ToolParameterType.STRING,
                    description="Math expression",
                )
            ],
        )
        async def calculate(expression: str) -> dict:
            return {"result": eval(expression)}

        # Check that tool definition is attached
        assert hasattr(calculate, "_tool_definition")
        assert calculate._tool_definition.name == "calculate"

        # Test execution
        result = await calculate(expression="2 + 2")
        assert result["result"] == 4


class TestBuiltInTools:
    """Test built-in tool definitions."""

    def test_default_registry(self):
        """Test that default registry has built-in tools."""
        from app.integrations.tools import default_tool_registry

        tools = default_tool_registry.list_tools()
        tool_names = [t.name for t in tools]

        assert "search_documents" in tool_names
        assert "get_current_time" in tool_names
        assert "calculate" in tool_names
        assert "web_search" in tool_names

    def test_search_documents_tool_format(self):
        """Test search_documents tool format."""
        from app.integrations.tools import search_documents_tool

        openai = search_documents_tool.to_openai_format()
        anthropic = search_documents_tool.to_anthropic_format()

        assert openai["function"]["name"] == "search_documents"
        assert anthropic["name"] == "search_documents"
        assert "query" in openai["function"]["parameters"]["properties"]
