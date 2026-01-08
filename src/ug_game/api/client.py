"""UG Labs PUG API WebSocket client."""

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

from ..core.config import settings


class UGGameAPIError(Exception):
    """Base exception for UG Game API errors."""

    pass


class AuthenticationError(UGGameAPIError):
    """Authentication failed."""

    pass


class ConnectionError(UGGameAPIError):
    """WebSocket connection error."""

    pass


class UGGameClient:
    """WebSocket client for UG Labs PUG API interactions."""

    def __init__(self) -> None:
        self.access_token: Optional[str] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False

    async def authenticate_player(
        self, service_account_api_key: str, federated_id: str
    ) -> str:
        """Authenticate as a player and get access token."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "api_key": service_account_api_key,
                "federated_id": federated_id,
            }

            async with session.post(
                f"{settings.api_base_url}/api/auth/login", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise AuthenticationError(f"Player authentication failed: {error_text}")

                data = await response.json()
                self.access_token = data["access_token"]
                return self.access_token

    async def authenticate_developer(self, developer_api_key: str) -> str:
        """Authenticate as a developer and get access token."""
        async with aiohttp.ClientSession() as session:
            payload = {"api_key": developer_api_key}

            async with session.post(
                f"{settings.api_base_url}/api/auth/login", json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise AuthenticationError(f"Developer authentication failed: {error_text}")

                data = await response.json()
                self.access_token = data["access_token"]
                return self.access_token

    async def create_player(self, developer_api_key: str, external_id: str) -> Dict[str, Any]:
        """Create a new player using developer API key."""
        async with aiohttp.ClientSession() as session:
            # First authenticate as developer
            developer_token = await self.authenticate_developer(developer_api_key)

            # Create player
            headers = {"Authorization": f"Bearer {developer_token}"}
            payload = {"external_id": external_id}

            async with session.post(
                f"{settings.api_base_url}/api/players",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise UGGameAPIError(f"Player creation failed: {error_text}")

                return await response.json()

    async def connect(self) -> None:
        """Connect to WebSocket."""
        try:
            self.websocket = await websockets.connect(settings.websocket_url)
            self.is_connected = True
        except WebSocketException as e:
            raise ConnectionError(f"Failed to connect to WebSocket: {e}")

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False

    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the WebSocket."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")

        await self.websocket.send(json.dumps(message))

    async def receive_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Receive messages from WebSocket as async generator."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")

        try:
            async for message in self.websocket:
                data = json.loads(message)
                yield data
        except ConnectionClosedError:
            self.is_connected = False
            raise ConnectionError("WebSocket connection closed")

    async def authenticate_websocket(self) -> Dict[str, Any]:
        """Authenticate on WebSocket."""
        if not self.access_token:
            raise AuthenticationError("No access token available")

        message = {
            "type": "request",
            "kind": "authenticate",
            "access_token": self.access_token,
            "uid": str(uuid.uuid4()),
            "client_start_time": asyncio.get_event_loop().time(),
        }

        await self.send_message(message)

        # Wait for response
        async for response in self.receive_messages():
            if response.get("kind") == "authenticate":
                return response
            break

        raise AuthenticationError("Authentication failed")

    async def set_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Set AI configuration."""
        message = {
            "type": "request",
            "kind": "set_configuration",
            "config": config,
            "uid": str(uuid.uuid4()),
            "client_start_time": asyncio.get_event_loop().time(),
        }

        await self.send_message(message)

        # Wait for response
        async for response in self.receive_messages():
            if response.get("kind") == "set_configuration":
                return response
            break

        raise UGGameAPIError("Configuration failed")

    async def send_text_interaction(
        self, text: str, audio_output: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Send text interaction and yield responses."""
        message = {
            "type": "stream",
            "kind": "interact",
            "text": text,
            "audio_output": audio_output,
            # "audio_input": False,  # Explicitly indicate this is text-only
            "uid": str(uuid.uuid4()),
            "client_start_time": asyncio.get_event_loop().time(),
        }

        # if audio_output:
            # message["audio_output"] = audio_output

        print(f"DEBUG: Sending interact message: {message}")
        await self.send_message(message)

        # Yield responses until interaction is complete
        async for response in self.receive_messages():
            yield response
            if response.get("kind") == "close":
                break

    async def send_audio_transcription(
        self, audio_data: bytes, language_code: str = "en", sample_rate: int = 16000
    ) -> str:
        """Send audio data for transcription using the correct UG Labs Transcription API protocol."""
        import base64
        import io
        import wave

        # Convert raw PCM to WAV format using the actual sample rate from recording
        channels = 1
        sample_width = 2  # 16-bit = 2 bytes

        # Create WAV data in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)

        wav_bytes = wav_buffer.getvalue()

        # Generate unique ID for this transcription session
        transcription_uid = str(uuid.uuid4())
        chunk_size = 32000  # 32KB as recommended by docs

        # Send audio in chunks
        for i in range(0, len(wav_bytes), chunk_size):
            chunk = wav_bytes[i:i + chunk_size]
            audio_b64 = base64.b64encode(chunk).decode('utf-8')

            message = {
                "type": "request",
                "uid": transcription_uid,
                "kind": "add_audio",
                "timestamp": asyncio.get_event_loop().time(),
                "audio": audio_b64,
                "config": {
                    "sampling_rate": sample_rate,
                    "mime_type": "audio/wav"
                }
            }

            await self.send_message(message)

            # Wait for acknowledgment (optional, but good practice)
            try:
                async for response in self.receive_messages():
                    if response.get("uid") == transcription_uid:
                        break
            except Exception:
                pass  # Continue if no ack received

        # Request transcription
        transcribe_message = {
            "type": "request",
            "uid": transcription_uid,
            "kind": "transcribe",
            "timestamp": asyncio.get_event_loop().time(),
            "language_code": language_code
        }

        await self.send_message(transcribe_message)

        # Wait for transcription response with timeout
        timeout = 10.0  # 10 second timeout
        try:
            async with asyncio.timeout(timeout):
                async for response in self.receive_messages():
                    print(f"DEBUG: Received response: {response}")  # Debug all responses
                    if (response.get("kind") == "transcribe" and
                        response.get("uid") == transcription_uid):
                        transcribed_text = response.get("text", "")
                        print(f"DEBUG: Found transcription response: '{transcribed_text}'")
                        return transcribed_text
        except asyncio.TimeoutError:
            print(f"DEBUG: Transcription timeout after {timeout} seconds")
            return ""

        print("DEBUG: No transcription response received")
        return ""  # Return empty string if no transcription received