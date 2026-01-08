#!/usr/bin/env python3
"""
Script to create a player using UG Labs PUG API.
This script creates a new player and returns the federated_id needed for the interact script.
"""

import asyncio
import json
import aiohttp
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
DEVELOPER_API_KEY = os.getenv('DEVELOPER_API_KEY', os.getenv('SERVICE_ACCOUNT_API_KEY', 'your-developer-api-key'))
BASE_URL = "https://pug.stg.uglabs.app"

async def get_developer_access_token():
    """Get developer access token for creating players."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "api_key": DEVELOPER_API_KEY
        }

        async with session.post(f"{BASE_URL}/api/auth/login", json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Failed to get developer access token: {response.status} - {error_text}")

            data = await response.json()
            return data["access_token"]

async def create_player(external_id):
    """Create a new player and return the federated_id."""
    print("Getting developer access token...")
    try:
        access_token = await get_developer_access_token()
        print("✓ Got developer access token")
    except Exception as e:
        print(f"✗ Failed to get developer access token: {e}")
        return None

    print(f"Creating player with external_id: {external_id}")

    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "external_id": external_id
        }

        async with session.post(f"{BASE_URL}/api/players", headers=headers, json=payload) as response:
            if response.status != 201:
                error_text = await response.text()
                raise Exception(f"Failed to create player: {response.status} - {error_text}")

            data = await response.json()
            print("✓ Player created successfully!")
            print(f"  Player PK: {data['pk']}")
            print(f"  External ID: {data['external_id']}")
            print(f"  Federated ID: {data['federated_id']}")

            return data['federated_id']

async def main():
    """Main function to create a player."""
    print("UG Labs PUG API - Create Player Script")
    print("=" * 50)

    # Check if DEVELOPER_API_KEY is set
    if DEVELOPER_API_KEY == 'your-developer-api-key':
        print("⚠️  Please set DEVELOPER_API_KEY in your .env file")
        print("   Get it from: https://pug-playground.stg.uglabs.app/profile")
        print("   (This is different from the Service Account API Key)")
        return

    # Ask for external_id
    external_id = input("Enter an external ID for the player (e.g., email or username): ").strip()

    if not external_id:
        print("✗ External ID cannot be empty")
        return

    try:
        federated_id = await create_player(external_id)

        if federated_id:
            print("\n" + "=" * 50)
            print("SUCCESS! Add this to your .env file:")
            print(f"PLAYER_FEDERATED_ID={federated_id}")
            print("=" * 50)

            # Optionally update .env file
            update_env = input("\nUpdate .env file automatically? (y/N): ").strip().lower()
            if update_env == 'y':
                try:
                    with open('.env', 'a') as f:
                        f.write(f"\nPLAYER_FEDERATED_ID={federated_id}\n")
                    print("✓ Updated .env file")
                except Exception as e:
                    print(f"✗ Failed to update .env file: {e}")

    except Exception as e:
        print(f"✗ Error creating player: {e}")

if __name__ == "__main__":
    asyncio.run(main())