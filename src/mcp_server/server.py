"""MCP Server implementation for UG Game SDK."""

import os
import sys
from typing import Any, Dict, List, Sequence

from mcp.server import InitializationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    PromptMessage,
    Resource,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolsCapability,
)

from .tools import TextChatTool, UGGameTools, VoiceChatTool


class UGGameMCPServer:
    """MCP Server for UG Game text and voice interactions."""

    def __init__(self):
        self.server = Server("ug-game-mcp")
        self.tools = UGGameTools()
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="text_chat",
                    description="Send a text message to the UG Game AI and receive a response",
                    inputSchema=TextChatTool.model_json_schema(),
                ),
                Tool(
                    name="voice_chat",
                    description="Record voice input and send it to the UG Game AI for transcription and response",
                    inputSchema=VoiceChatTool.model_json_schema(),
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            print(f"DEBUG: Handling tool call: {name} with args: {arguments}", file=sys.stderr)
            try:
                if name == "text_chat":
                    tool = TextChatTool(**arguments)
                    result = await self.tools.send_text_message(tool)

                    if result.get("success"):
                        content = f"AI Response: {result['text']}"
                        if result.get("has_audio"):
                            content += f"\n(Audio response available: {result['audio_size']} bytes)"
                    else:
                        content = f"Error: {result['error']}"

                elif name == "voice_chat":
                    tool = VoiceChatTool(**arguments)
                    result = await self.tools.send_voice_message(tool)

                    if result.get("success"):
                        content = f"Transcription: {result.get('transcription', 'N/A')}\nAI Response: {result['text']}"
                        if result.get("has_audio"):
                            content += f"\n(Audio response available: {result['audio_size']} bytes)"
                    else:
                        content = f"Error: {result['error']}"

                else:
                    content = f"Unknown tool: {name}"

                return CallToolResult(content=[TextContent(type="text", text=content)])

            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Tool execution failed: {str(e)}")],
                    isError=True,
                )

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources (none for now)."""
            return []

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> Sequence[EmbeddedResource]:
            """Read a resource (not implemented)."""
            raise ValueError(f"Resource not found: {uri}")

        @self.server.list_prompts()
        async def handle_list_prompts() -> List[Dict[str, Any]]:
            """List available prompts (none for now)."""
            return []

        @self.server.get_prompt()
        async def handle_get_prompt(
            name: str, arguments: Dict[str, Any]
        ) -> Sequence[PromptMessage]:
            """Get a prompt (not implemented)."""
            raise ValueError(f"Prompt not found: {name}")

    async def initialize_session(self) -> None:
        """Initialize the UG Game chat session."""
        service_account_api_key = os.getenv("SERVICE_ACCOUNT_API_KEY")
        player_federated_id = os.getenv("PLAYER_FEDERATED_ID")

        print(
            f"DEBUG: Initializing session with key={service_account_api_key[:10]}... and id={player_federated_id[:10]}...",
            file=sys.stderr,
        )

        if not service_account_api_key:
            raise ValueError("SERVICE_ACCOUNT_API_KEY environment variable is required")
        if not player_federated_id:
            raise ValueError("PLAYER_FEDERATED_ID environment variable is required")

        await self.tools.initialize(
            service_account_api_key=service_account_api_key, player_federated_id=player_federated_id
        )
        print("DEBUG: Session initialized successfully", file=sys.stderr)

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.tools.cleanup()

    async def run(self) -> None:
        """Run the MCP server."""
        try:
            await self.initialize_session()
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    initialization_options=InitializationOptions(
                        server_name="ug-game-mcp",
                        server_version="1.0.0",
                        capabilities=ServerCapabilities(tools=ToolsCapability()),
                    ),
                )
        finally:
            await self.cleanup()
