"""MCP tool loader with real MCP client integration."""

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Optional imports for URL-based transports
try:
    from mcp.client.sse import sse_client
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False
    sse_client = None

try:
    from mcp.client.websocket import websocket_client
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    websocket_client = None

from .base import Tool, ToolResult


class MCPTool(Tool):
    """Wrapper for MCP tools."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        session: ClientSession,
    ):
        self._name = name
        self._description = description
        self._parameters = parameters
        self._session = session

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs) -> ToolResult:
        """Execute MCP tool via the session."""
        try:
            result = await self._session.call_tool(self._name, arguments=kwargs)

            # MCP tool results are a list of content items
            content_parts = []
            for item in result.content:
                if hasattr(item, 'text'):
                    content_parts.append(item.text)
                else:
                    content_parts.append(str(item))

            content_str = '\n'.join(content_parts)

            is_error = result.isError if hasattr(result, 'isError') else False

            return ToolResult(
                success=not is_error,
                content=content_str,
                error=None if not is_error else "Tool returned error"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"MCP tool execution failed: {str(e)}"
            )


class MCPServerConnection:
    """Manages connection to a single MCP server."""

    def __init__(
        self,
        name: str,
        transport: str = "stdio",
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        url: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.name = name
        self.transport = transport.lower()
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.url = url
        self.headers = headers or {}
        self.session: ClientSession | None = None
        self.exit_stack: AsyncExitStack | None = None
        self.tools: list[MCPTool] = []

    async def connect(self) -> bool:
        """Connect to the MCP server using proper async context management."""
        try:
            # Use AsyncExitStack to properly manage multiple async context managers
            self.exit_stack = AsyncExitStack()
            
            # Create appropriate client based on transport type
            if self.transport == "stdio":
                if not self.command:
                    raise ValueError(f"Command is required for stdio transport (server: {self.name})")
                
                server_params = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    env=self.env if self.env else None
                )
                read_stream, write_stream = await self.exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                
            elif self.transport == "sse":
                if not SSE_AVAILABLE:
                    raise ImportError(
                        f"SSE transport not available for server '{self.name}'. "
                        "Please install with: pip install 'mcp[sse]' or upgrade mcp package."
                    )
                if not self.url:
                    raise ValueError(f"URL is required for SSE transport (server: {self.name})")
                
                result = await self.exit_stack.enter_async_context(
                    sse_client(url=self.url, headers=self.headers)
                )
                # SSE client returns (read, write) or (read, write, cleanup)
                if isinstance(result, tuple):
                    if len(result) == 2:
                        read_stream, write_stream = result
                    elif len(result) == 3:
                        read_stream, write_stream, _ = result
                    else:
                        raise ValueError(f"Unexpected SSE client result: {result}")
                else:
                    raise ValueError(f"Unexpected SSE client result type: {type(result)}")
                    
            elif self.transport in ["http", "websocket", "ws"]:
                if not WEBSOCKET_AVAILABLE:
                    raise ImportError(
                        f"WebSocket transport not available for server '{self.name}'. "
                        "Please upgrade mcp package to a version that supports WebSocket."
                    )
                if not self.url:
                    raise ValueError(f"URL is required for WebSocket transport (server: {self.name})")
                
                result = await self.exit_stack.enter_async_context(
                    websocket_client(url=self.url, headers=self.headers)
                )
                # WebSocket client returns (read, write) or (read, write, cleanup)
                if isinstance(result, tuple):
                    if len(result) == 2:
                        read_stream, write_stream = result
                    elif len(result) == 3:
                        read_stream, write_stream, _ = result
                    else:
                        raise ValueError(f"Unexpected WebSocket client result: {result}")
                else:
                    raise ValueError(f"Unexpected WebSocket client result type: {type(result)}")
                    
            else:
                raise ValueError(
                    f"Unsupported transport type '{self.transport}' for server '{self.name}'. "
                    "Use 'stdio', 'sse', or 'websocket'/'ws'"
                )
            
            # Enter client session context
            session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            self.session = session

            # Initialize the session
            await session.initialize()

            # List available tools
            tools_list = await session.list_tools()

            # Wrap each tool
            for tool in tools_list.tools:
                # Convert MCP tool schema to our format
                parameters = tool.inputSchema if hasattr(tool, 'inputSchema') else {}

                mcp_tool = MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=parameters,
                    session=session
                )
                self.tools.append(mcp_tool)

            print(f"✓ Connected to MCP server '{self.name}' ({self.transport}) - loaded {len(self.tools)} tools")
            for tool in self.tools:
                desc = tool.description[:60] if len(tool.description) > 60 else tool.description
                print(f"  - {tool.name}: {desc}...")
            return True

        except Exception as e:
            print(f"✗ Failed to connect to MCP server '{self.name}' ({self.transport}): {e}")
            # Clean up exit stack if connection failed
            if self.exit_stack:
                await self.exit_stack.aclose()
                self.exit_stack = None
            import traceback
            traceback.print_exc()
            return False

    async def disconnect(self):
        """Properly disconnect from the MCP server."""
        if self.exit_stack:
            try:
                # AsyncExitStack handles all cleanup properly
                await self.exit_stack.aclose()
            except RuntimeError as e:
                # Ignore "Attempted to exit cancel scope in a different task" errors
                # This can happen during program shutdown
                if "cancel scope" not in str(e):
                    raise
            except Exception as e:
                # Log but don't raise other exceptions during cleanup
                print(f"Warning: Error during disconnect of '{self.name}': {e}")
            finally:
                self.exit_stack = None
                self.session = None


# Global connections registry
_mcp_connections: list[MCPServerConnection] = []


async def load_mcp_tools_async(config_path: str = "mcp.json") -> list[Tool]:
    """
    Load MCP tools from config file.

    This function:
    1. Reads the MCP config file
    2. Starts MCP server processes or connects to remote servers
    3. Connects to each server
    4. Fetches tool definitions
    5. Wraps them as Tool objects

    Supported transport types:
    - stdio: Local process communication (command-based)
    - sse: Server-Sent Events (URL-based)
    - websocket: WebSocket connection (URL-based)

    Config format:
    {
      "mcpServers": {
        "server-name": {
          "transport": "stdio|sse|websocket",
          "command": "...",      // for stdio
          "args": [...],         // for stdio
          "env": {...},          // for stdio
          "url": "...",          // for sse/websocket
          "headers": {...},      // for sse/websocket (optional)
          "disabled": false      // optional
        }
      }
    }

    Args:
        config_path: Path to MCP configuration file (default: "mcp.json")

    Returns:
        List of Tool objects representing MCP tools
    """
    global _mcp_connections

    config_file = Path(config_path)

    if not config_file.exists():
        print(f"MCP config not found: {config_path}")
        return []

    try:
        with open(config_file, encoding="utf-8") as f:
            config = json.load(f)

        mcp_servers = config.get("mcpServers", {})

        if not mcp_servers:
            print("No MCP servers configured")
            return []

        all_tools = []

        # Connect to each enabled server
        for server_name, server_config in mcp_servers.items():
            if server_config.get("disabled", False):
                print(f"Skipping disabled server: {server_name}")
                continue

            # Detect transport type (default to stdio for backward compatibility)
            transport = server_config.get("transport", "stdio")
            
            # Extract configuration based on transport type
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            url = server_config.get("url")
            headers = server_config.get("headers", {})

            # Validate required fields
            if transport == "stdio" and not command:
                print(f"⚠️  No command specified for stdio server: {server_name}")
                continue
            
            if transport in ["sse", "websocket", "ws"] and not url:
                print(f"⚠️  No URL specified for {transport} server: {server_name}")
                continue

            connection = MCPServerConnection(
                name=server_name,
                transport=transport,
                command=command,
                args=args,
                env=env,
                url=url,
                headers=headers,
            )
            success = await connection.connect()

            if success:
                _mcp_connections.append(connection)
                all_tools.extend(connection.tools)

        print(f"\nTotal MCP tools loaded: {len(all_tools)}")

        return all_tools

    except Exception as e:
        print(f"Error loading MCP config: {e}")
        import traceback
        traceback.print_exc()
        return []


async def cleanup_mcp_connections():
    """Clean up all MCP connections."""
    global _mcp_connections
    
    # Disconnect all connections, catching any errors
    errors = []
    for connection in _mcp_connections:
        try:
            await connection.disconnect()
        except Exception as e:
            errors.append(f"{connection.name}: {e}")
    
    _mcp_connections.clear()
    
    # Report errors if any (but don't raise)
    if errors:
        print(f"⚠️  Some connections had errors during cleanup:")
        for error in errors:
            print(f"   - {error}")
