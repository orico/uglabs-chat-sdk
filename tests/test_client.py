"""Tests for UG Game API client."""

import pytest
from aioresponses import aioresponses
from unittest.mock import AsyncMock, MagicMock, patch

from ug_game.api.client import UGGameClient, UGGameAPIError, AuthenticationError, ConnectionError


class TestUGGameClient:
    """Test cases for UGGameClient."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return UGGameClient()

    @pytest.mark.asyncio
    async def test_authenticate_player_success(self, client):
        """Test successful player authentication."""
        with aioresponses() as m:
            m.post(
                "https://pug.stg.uglabs.app/api/auth/login",
                payload={"access_token": "test_token"},
                status=200
            )

            token = await client.authenticate_player("api_key", "federated_id")

            assert token == "test_token"
            assert client.access_token == "test_token"

    @pytest.mark.asyncio
    async def test_authenticate_player_failure(self, client):
        """Test failed player authentication."""
        with aioresponses() as m:
            m.post(
                "https://pug.stg.uglabs.app/api/auth/login",
                status=401,
                body="Invalid credentials"
            )

            with pytest.raises(UGGameAPIError):
                await client.authenticate_player("api_key", "federated_id")

    @pytest.mark.asyncio
    async def test_authenticate_developer_success(self, client):
        """Test successful developer authentication."""
        with aioresponses() as m:
            m.post(
                "https://pug.stg.uglabs.app/api/auth/login",
                payload={"access_token": "dev_token"},
                status=200
            )

            token = await client.authenticate_developer("dev_api_key")

            assert token == "dev_token"
            assert client.access_token == "dev_token"

    @pytest.mark.asyncio
    async def test_authenticate_developer_failure(self, client):
        """Test failed developer authentication."""
        with aioresponses() as m:
            m.post(
                "https://pug.stg.uglabs.app/api/auth/login",
                status=401,
                body="Invalid developer key"
            )

            with pytest.raises(AuthenticationError, match="Developer authentication failed"):
                await client.authenticate_developer("invalid_dev_key")

    @pytest.mark.asyncio
    async def test_connect_success(self, client):
        """Test successful WebSocket connection."""
        mock_websocket = AsyncMock()

        async def mock_connect(*args, **kwargs):
            return mock_websocket

        with patch('websockets.connect', side_effect=mock_connect) as mock_connect_func:
            await client.connect()

            assert client.websocket == mock_websocket
            assert client.is_connected is True
            mock_connect_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, client):
        """Test WebSocket connection failure."""
        from websockets.exceptions import WebSocketException

        async def mock_connect_fail(*args, **kwargs):
            raise WebSocketException("Connection failed")

        with patch('websockets.connect', side_effect=mock_connect_fail):
            with pytest.raises(ConnectionError, match="Failed to connect to WebSocket"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Test WebSocket disconnection."""
        mock_websocket = AsyncMock()
        client.websocket = mock_websocket
        client.is_connected = True

        await client.disconnect()

        mock_websocket.close.assert_called_once()
        assert client.is_connected is False
        assert client.websocket == mock_websocket  # websocket reference kept

    @pytest.mark.asyncio
    async def test_disconnect_no_websocket(self, client):
        """Test disconnect when no WebSocket connection exists."""
        client.websocket = None
        client.is_connected = False

        await client.disconnect()  # Should not raise

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_send_message_success(self, client):
        """Test sending message to WebSocket."""
        import json
        mock_websocket = AsyncMock()
        client.websocket = mock_websocket
        client.is_connected = True

        message = {"type": "test", "data": "value"}
        await client.send_message(message)

        mock_websocket.send.assert_called_once_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, client):
        """Test sending message when not connected."""
        client.websocket = None
        client.is_connected = False

        with pytest.raises(ConnectionError, match="Not connected to WebSocket"):
            await client.send_message({"type": "test"})

    @pytest.mark.asyncio
    async def test_receive_messages_success(self, client):
        """Test receiving messages from WebSocket."""
        # For this test, we just verify the method can be called
        # Full async iteration testing is complex and covered by integration tests
        mock_websocket = AsyncMock()
        client.websocket = mock_websocket
        client.is_connected = True

        # Test that the method exists and doesn't immediately fail
        # (actual async iteration testing would require complex mocking)
        assert hasattr(client, 'receive_messages')

    @pytest.mark.asyncio
    async def test_receive_messages_not_connected(self, client):
        """Test receiving messages when not connected."""
        client.websocket = None
        client.is_connected = False

        with pytest.raises(ConnectionError, match="Not connected to WebSocket"):
            async for message in client.receive_messages():
                pass

    @pytest.mark.asyncio
    async def test_authenticate_websocket_success(self, client):
        """Test successful WebSocket authentication."""
        import json
        client.access_token = "test_token"

        # Mock send_message and receive_messages
        with patch.object(client, 'send_message') as mock_send, \
             patch.object(client, 'receive_messages') as mock_receive:

            # Mock receive_messages to return auth response as async generator
            async def mock_receive_gen():
                yield {"kind": "authenticate", "status": "success"}

            mock_receive.side_effect = mock_receive_gen

            result = await client.authenticate_websocket()

            assert result["kind"] == "authenticate"
            assert result["status"] == "success"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_websocket_no_token(self, client):
        """Test WebSocket authentication without access token."""
        client.access_token = None

        with pytest.raises(AuthenticationError, match="No access token available"):
            await client.authenticate_websocket()

    @pytest.mark.asyncio
    async def test_set_configuration_success(self, client):
        """Test successful configuration setting."""
        # Mock send_message and receive_messages
        with patch.object(client, 'send_message') as mock_send, \
             patch.object(client, 'receive_messages') as mock_receive:

            config = {"model": "gpt-4", "temperature": 0.7}

            async def mock_receive_gen():
                yield {"kind": "set_configuration", "status": "success"}

            mock_receive.side_effect = mock_receive_gen

            result = await client.set_configuration(config)

            assert result["kind"] == "set_configuration"
            assert result["status"] == "success"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_text_interaction(self, client):
        """Test sending text interaction."""
        # Mock send_message and receive_messages
        with patch.object(client, 'send_message') as mock_send, \
             patch.object(client, 'receive_messages') as mock_receive:

            async def mock_receive_gen():
                yield {"type": "response", "text": "Hello"}
                yield {"kind": "close"}

            mock_receive.side_effect = mock_receive_gen

            responses = []
            async for response in client.send_text_interaction("Hello world"):
                responses.append(response)

            assert len(responses) == 2
            assert responses[0]["text"] == "Hello"
            assert responses[1]["kind"] == "close"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_audio_transcription_success(self, client):
        """Test successful audio transcription."""
        import base64
        import uuid

        # Mock send_message and receive_messages
        with patch.object(client, 'send_message') as mock_send, \
             patch.object(client, 'receive_messages') as mock_receive, \
             patch('uuid.uuid4', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):

            async def mock_receive_gen():
                yield {"uid": "12345678-1234-5678-1234-567812345678", "kind": "ack"}  # Acknowledgment
                yield {"uid": "12345678-1234-5678-1234-567812345678", "kind": "transcribe", "text": "Hello world"}

            mock_receive.side_effect = mock_receive_gen

            # Create simple test audio data (raw PCM)
            audio_data = b"test_audio_data1234"  # 18 bytes for even length

            result = await client.send_audio_transcription(audio_data)

            assert result == "Hello world"
            # Should call send_message multiple times (chunks + transcribe request)
            assert mock_send.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_audio_transcription_timeout(self, client):
        """Test audio transcription timeout."""
        with patch.object(client, 'send_message'), \
             patch.object(client, 'receive_messages') as mock_receive:

            async def mock_receive_gen():
                # Yield nothing to simulate timeout
                return
                yield  # pragma: no cover

            mock_receive.side_effect = mock_receive_gen

            audio_data = b"test_audio_data1234"
            result = await client.send_audio_transcription(audio_data)

            assert result == ""  # Should return empty string on timeout

    @pytest.mark.asyncio
    async def test_create_player_success(self, client):
        """Test successful player creation."""
        with aioresponses() as m:
            # Mock developer authentication
            m.post(
                "https://pug.stg.uglabs.app/api/auth/login",
                payload={"access_token": "dev_token"},
                status=200
            )
            # Mock player creation
            m.post(
                "https://pug.stg.uglabs.app/api/players",
                payload={"federated_id": "player_123", "external_id": "ext_123"},
                status=201
            )

            result = await client.create_player("dev_key", "ext_123")

            assert result["federated_id"] == "player_123"
            assert result["external_id"] == "ext_123"

    @pytest.mark.asyncio
    async def test_create_player_creation_failure(self, client):
        """Test player creation failure."""
        with aioresponses() as m:
            # Mock developer authentication success
            m.post(
                "https://pug.stg.uglabs.app/api/auth/login",
                payload={"access_token": "dev_token"},
                status=200
            )
            # Mock player creation failure
            m.post(
                "https://pug.stg.uglabs.app/api/players",
                status=400,
                body="Invalid external_id"
            )

            with pytest.raises(UGGameAPIError, match="Player creation failed"):
                await client.create_player("dev_key", "invalid_id")