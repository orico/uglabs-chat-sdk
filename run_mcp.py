#!/usr/bin/env python3
"""Entry point for the UG Game MCP Server."""

import asyncio
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Add src to path so we can import the mcp module
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.mcp_server import UGGameMCPServer

load_dotenv(override=False)  # Don't override env vars set by Claude Desktop


async def main():
    """Run the MCP server."""
    server = UGGameMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
