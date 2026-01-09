#!/usr/bin/env python3
"""Demo script showing UG Game chat functionality."""

import asyncio
import os
import sys
from pathlib import Path

from pydantic import SecretStr

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ug_game.api.client import UGGameClient  # noqa: E402
from ug_game.core.config import settings  # noqa: E402


async def demo_chat() -> None:
    """Demo a simple chat interaction."""
    print("🎪 UG Game Chat Demo")
    print("=" * 50)

    # Set demo credentials from environment
    api_key = os.getenv("SERVICE_ACCOUNT_API_KEY")
    federated_id = os.getenv("PLAYER_FEDERATED_ID")

    if not api_key or not federated_id:
        print("❌ Please set SERVICE_ACCOUNT_API_KEY and PLAYER_FEDERATED_ID environment variables")
        return

    settings.service_account_api_key = SecretStr(api_key)
    settings.player_federated_id = federated_id

    client = UGGameClient()

    try:
        print("🔐 Authenticating...")
        assert settings.service_account_api_key is not None
        await client.authenticate_player(
            settings.service_account_api_key.get_secret_value(), settings.player_federated_id
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
