#!/usr/bin/env python3
"""Demo script showing UG Game chat functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ug_game.api.client import UGGameClient
from ug_game.core.config import settings


async def demo_chat():
    """Demo a simple chat interaction."""
    print("🎪 UG Game Chat Demo")
    print("=" * 50)

    # Set demo credentials from environment
    settings.service_account_api_key = os.getenv("SERVICE_ACCOUNT_API_KEY")
    settings.player_federated_id = os.getenv("PLAYER_FEDERATED_ID")

    if not settings.service_account_api_key or not settings.player_federated_id:
        print("❌ Please set SERVICE_ACCOUNT_API_KEY and PLAYER_FEDERATED_ID environment variables")
        return

    client = UGGameClient()

    try:
        print("🔐 Authenticating...")
        await client.authenticate_player(
            settings.service_account_api_key.get_secret_value(),
            settings.player_federated_id
        )
        print("✅ Authentication successful")

        print("🔌 Connecting to WebSocket...")
        await client.connect()
        print("✅ Connected")

        print("🤝 Authenticating WebSocket...")
        await client.authenticate_websocket()
        print("✅ WebSocket authenticated")

        print("⚙️ Setting configuration...")
        await client.set_configuration({"prompt": settings.default_prompt})
        print("✅ Configuration set")

        print("\n💬 Sending demo message...")
        demo_message = "Hello! Tell me about yourself in one sentence."

        # Send message and collect responses
        responses = []
        async for response in client.send_text_interaction(demo_message, audio_output=False):
            if response.get("event") == "text":
                responses.append(response.get("text", ""))

        if responses:
            full_response = "".join(responses)
            print(f"🤖 AI Response: {full_response}")
            print("\n✅ Demo completed successfully!")
        else:
            print("❌ No response received")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(demo_chat())