"""Unit tests for SDK ChatSession."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from ug_game.sdk.session import ChatSession
from ug_game.sdk.types import ChatCallbacks, ChatConfig, ChatResponse
from ug_game.api.client import UGGameAPIError
from tests.conftest import create_test_audio_data, verify_chat_response


class TestChatSession:
    """Test cases for SDK ChatSession."""

    @pytest.fixture
    def callbacks(self):
        """Create test callbacks."""
        return ChatCallbacks()

    @pytest.fixture
    def config(self):
        """Create test config."""
        return ChatConfig(debug_mode=True)

    @pytest.fixture
    def session(self, callbacks, config):
        """Create test session."""
        return ChatSession(callbacks=callbacks, config=config)

    @pytest.mark.asyncio
    async def test_initialization_success(self, session, mock_api_client):
        """Test successful session initialization."""
        session.client = mock_api_client
        
        # Mock authentication and connection
        session.client.authenticate_player = AsyncMock(return_value="test_token")
        session.client.connect = AsyncMock()
        session.client.authenticate_websocket = AsyncMock(return_value={"kind": "authenticate"})
        session.client.set_configuration = AsyncMock(return_value={"kind": "set_configuration"})
        
        await session.initialize("test_key", "test_player", "test prompt")
        
        assert session.is_connected
        assert session.system_prompt == "test prompt"

    @pytest.mark.asyncio
    async def test_initialization_failure(self, session):
        """Test initialization failure."""
        session.client.authenticate_player = AsyncMock(side_effect=UGGameAPIError("Auth failed"))
        
        with pytest.raises(UGGameAPIError):
            await session.initialize("test_key", "test_player")

    @pytest.mark.asyncio
    async def test_send_text_success(self, session, mock_api_client):
        """Test successful text message send."""
        session.client = mock_api_client
        session.is_connected = True
        
        # Mock text interaction responses
        async def mock_text_interaction(*args, **kwargs):
            yield {"event": "text", "text": "Hello"}
            yield {"event": "text", "text": " World"}
            yield {"kind": "close"}
        
        session.client.send_text_interaction = mock_text_interaction
        
        response = await session.send_text("Hi")
        
        assert response.text == "Hello World"
        assert response.error is None
        assert len(session.message_history) == 1

    @pytest.mark.asyncio
    async def test_send_text_with_audio(self, session, mock_api_client):
        """Test text message with audio response."""
        session.client = mock_api_client
        session.is_connected = True
        session.config.audio_output = True
        
        # Mock responses with audio
        async def mock_text_interaction(*args, **kwargs):
            yield {"event": "text", "text": "Hello"}
            yield {"event": "audio", "audio": b"test_audio_data"}
            yield {"kind": "close"}
        
        session.client.send_text_interaction = mock_text_interaction
        
        response = await session.send_text("Hi", audio_output=True)
        
        assert response.text == "Hello"
        assert response.audio is not None
        assert response.error is None

    @pytest.mark.asyncio
    async def test_send_text_not_connected(self, session):
        """Test sending text when not connected."""
        session.is_connected = False
        
        with pytest.raises(UGGameAPIError):
            await session.send_text("Hi")

    @pytest.mark.asyncio
    async def test_send_voice_success(self, session, mock_api_client):
        """Test successful voice message send."""
        session.client = mock_api_client
        session.is_connected = True
        
        audio_data = create_test_audio_data()
        
        # Mock transcription
        session.client.send_audio_transcription = AsyncMock(return_value="test transcription")
        
        # Mock reconnection
        session.client.disconnect = AsyncMock()
        session.client.connect = AsyncMock()
        session.client.authenticate_websocket = AsyncMock(return_value={"kind": "authenticate"})
        session.client.set_configuration = AsyncMock(return_value={"kind": "set_configuration"})
        
        # Mock text interaction
        async def mock_text_interaction(*args, **kwargs):
            yield {"event": "text", "text": "Response to voice"}
            yield {"kind": "close"}
        
        session.client.send_text_interaction = mock_text_interaction
        
        response = await session.send_voice(audio_data)
        
        assert response.transcription == "test transcription"
        assert response.text == "Response to voice"
        assert response.error is None

    @pytest.mark.asyncio
    async def test_send_voice_transcription_failure(self, session, mock_api_client):
        """Test voice send with transcription failure."""
        session.client = mock_api_client
        session.is_connected = True
        
        audio_data = create_test_audio_data()
        
        # Mock transcription failure
        session.client.send_audio_transcription = AsyncMock(return_value="")
        
        response = await session.send_voice(audio_data)
        
        assert response.error is not None
        assert "Transcription failed" in str(response.error)

    @pytest.mark.asyncio
    async def test_record_and_send_voice(self, session, mock_api_client):
        """Test record and send voice."""
        session.client = mock_api_client
        session.is_connected = True
        
        audio_data = create_test_audio_data()
        
        # Mock recording
        with patch('ug_game.sdk.session.record_voice_input_async', new_callable=AsyncMock) as mock_record:
            mock_record.return_value = audio_data
            
            # Mock transcription
            session.client.send_audio_transcription = AsyncMock(return_value="test transcription")
            
            # Mock reconnection
            session.client.disconnect = AsyncMock()
            session.client.connect = AsyncMock()
            session.client.authenticate_websocket = AsyncMock(return_value={"kind": "authenticate"})
            session.client.set_configuration = AsyncMock(return_value={"kind": "set_configuration"})
            
            # Mock text interaction
            async def mock_text_interaction(*args, **kwargs):
                yield {"event": "text", "text": "Response"}
                yield {"kind": "close"}
            
            session.client.send_text_interaction = mock_text_interaction
            
            response = await session.record_and_send_voice(duration_seconds=1)
            
            assert response.transcription == "test transcription"
            assert response.text == "Response"
            mock_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_system_prompt(self, session, mock_api_client):
        """Test updating system prompt."""
        session.client = mock_api_client
        session.is_connected = True
        
        session.client.set_configuration = AsyncMock(return_value={"kind": "set_configuration"})
        
        await session.update_system_prompt("New prompt")
        
        assert session.system_prompt == "New prompt"
        session.client.set_configuration.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_player(self, session, mock_api_client):
        """Test creating a new player."""
        session.client = mock_api_client
        
        # Mock developer authentication and player creation
        session.client.authenticate_developer = AsyncMock(return_value="dev_token")
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(return_value={"federated_id": "test_player_id"})
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            player_data = await session.create_player("dev_key", "external_id")
            
            assert player_data["federated_id"] == "test_player_id"

    @pytest.mark.asyncio
    async def test_disconnect(self, session, mock_api_client):
        """Test disconnecting session."""
        session.client = mock_api_client
        session.is_connected = True
        
        session.client.disconnect = AsyncMock()
        
        await session.disconnect()
        
        assert not session.is_connected
        session.client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_callbacks_invocation(self, session, mock_api_client):
        """Test that callbacks are invoked correctly."""
        text_called = []
        audio_called = []
        error_called = []
        status_called = []
        
        session.callbacks = ChatCallbacks(
            on_text_response=lambda text: text_called.append(text),
            on_audio_response=lambda audio: audio_called.append(audio),
            on_error=lambda error: error_called.append(error),
            on_status_change=lambda status: status_called.append(status),
        )
        
        session.client = mock_api_client
        session.is_connected = True
        
        # Mock initialization
        session.client.authenticate_player = AsyncMock(return_value="test_token")
        session.client.connect = AsyncMock()
        session.client.authenticate_websocket = AsyncMock(return_value={"kind": "authenticate"})
        session.client.set_configuration = AsyncMock(return_value={"kind": "set_configuration"})
        
        await session.initialize("test_key", "test_player")
        
        # Check status callbacks were called
        assert len(status_called) > 0
        
        # Mock text interaction
        async def mock_text_interaction(*args, **kwargs):
            yield {"event": "text", "text": "Test"}
            yield {"kind": "close"}
        
        session.client.send_text_interaction = mock_text_interaction
        
        await session.send_text("Hi")
        
        # Check text callback was called
        assert len(text_called) > 0
        assert "Test" in text_called
