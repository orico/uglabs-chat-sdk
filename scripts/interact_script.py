#!/usr/bin/env python3
"""
Script to interact with UG Labs PUG API using text only (no voice).
This script demonstrates the basic interaction flow with the WebSocket API.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import websockets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration - you'll need to set these environment variables or replace with your values
SERVICE_ACCOUNT_API_KEY = os.getenv("SERVICE_ACCOUNT_API_KEY")
PLAYER_FEDERATED_ID = os.getenv("PLAYER_FEDERATED_ID")

# API endpoints
BASE_URL = "https://pug.stg.uglabs.app"
WS_URL = "wss://pug.stg.uglabs.app/interact"


async def get_access_token() -> str:
    """Get access token for player authentication."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        payload = {"api_key": SERVICE_ACCOUNT_API_KEY, "federated_id": PLAYER_FEDERATED_ID}

        async with session.post(f"{BASE_URL}/api/auth/login", json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Failed to get access token: {response.status} - {error_text}")

            data = await response.json()
            return str(data["access_token"])


async def interact_with_pug() -> None:
    """Main interaction function using WebSocket."""

    # Get access token
    print("Getting access token...")
    try:
        access_token = await get_access_token()
        print("✓ Got access token")
    except Exception as e:
        print(f"✗ Failed to get access token: {e}")
        return

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✓ Connected to WebSocket")

            # Step 1: Authenticate
            auth_uid = str(uuid.uuid4())
            auth_message = {
                "type": "request",
                "kind": "authenticate",
                "access_token": access_token,
                "uid": auth_uid,
                "client_start_time": datetime.now(timezone.utc).isoformat(),
            }

            print("Sending authentication...")
            await websocket.send(json.dumps(auth_message))

            # Wait for auth response
            auth_response = await websocket.recv()
            auth_data = json.loads(auth_response)
            print(f"✓ Authentication response: {auth_data.get('kind', 'unknown')}")

            # Step 2: Set configuration
            config_uid = str(uuid.uuid4())
            config_message = {
                "type": "request",
                "kind": "set_configuration",
                "config": {
                    "prompt": "You are a helpful AI assistant. Respond to user messages in a friendly and engaging way."
                },
                "uid": config_uid,
                "client_start_time": datetime.now(timezone.utc).isoformat(),
            }

            print("Setting configuration...")
            await websocket.send(json.dumps(config_message))

            # Wait for config response
            config_response = await websocket.recv()
            config_data = json.loads(config_response)
            print(f"✓ Configuration response: {config_data.get('kind', 'unknown')}")

            # Step 3: Send text interaction
            interact_uid = str(uuid.uuid4())
            text_message = "Hello! Can you tell me about yourself?"  # You can change this text

            interact_message = {
                "type": "stream",
                "kind": "interact",
                "text": text_message,
                "context": {},
                "audio_output": False,  # No voice output
                "uid": interact_uid,
                "client_start_time": datetime.now(timezone.utc).isoformat(),
            }

            print(f"Sending text message: '{text_message}'")
            await websocket.send(json.dumps(interact_message))

            # Step 4: Receive responses
            print("\nReceiving responses:")
            print("-" * 50)

            while True:
                try:
                    # Set a timeout for receiving messages
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)

                    if data.get("type") == "stream":
                        if data.get("kind") == "close":
                            print("✓ Interaction completed")
                            break
                        elif data.get("event") == "text":
                            print(f"AI Response: {data.get('text', '')}")
                        elif data.get("event") == "audio":
                            # Skip audio data since we want text only
                            continue
                        else:
                            print(f"Other event: {data}")

                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"Error receiving response: {e}")
                    break

    except Exception as e:
        print(f"✗ WebSocket error: {e}")


async def main() -> None:
    """Main function to run the interaction."""
    print("UG Labs PUG API Text Interaction Script")
    print("=" * 50)

    # Check if required environment variables are set
    if SERVICE_ACCOUNT_API_KEY == "your-service-account-api-key":
        print("⚠️  Please set SERVICE_ACCOUNT_API_KEY environment variable")
        print("   Get it from: https://pug-playground.stg.uglabs.app/service-accounts")
        return

    if PLAYER_FEDERATED_ID == "your-player-federated-id":
        print("⚠️  Please set PLAYER_FEDERATED_ID environment variable")
        print("   Get it from: https://pug-playground.stg.uglabs.app/players")
        return

    await interact_with_pug()


if __name__ == "__main__":
    asyncio.run(main())
