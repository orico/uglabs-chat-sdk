"""Pytest fixtures and helpers for UG Game SDK tests."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Optional

from ug_game.sdk.session import ChatSession
from ug_game.sdk.types import ChatCallbacks, ChatConfig
from ug_game.api.client import UGGameClient


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.send = AsyncMock()
    websocket.__aiter__ = AsyncMock(return_value=iter([]))
    return websocket


@pytest.fixture
def mock_api_client(mock_websocket):
    """Mock API client for unit tests."""
    client = UGGameClient()
    client.websocket = mock_websocket
    client.is_connected = True
    client.access_token = "test_token"
    return client


@pytest.fixture
def test_credentials():
    """
    Load test API credentials from environment.
    
    Returns:
        dict with service_account_api_key and player_federated_id, or None if not available
    """
    service_key = os.getenv("TEST_SERVICE_ACCOUNT_API_KEY")
    player_id = os.getenv("TEST_PLAYER_FEDERATED_ID")
    
    if service_key and player_id:
        return {
            "service_account_api_key": service_key,
            "player_federated_id": player_id,
        }
    return None


@pytest.fixture
def developer_credentials():
    """Load developer API credentials from environment."""
    dev_key = os.getenv("TEST_DEVELOPER_API_KEY")
    return {"developer_api_key": dev_key} if dev_key else None


@pytest.fixture
def test_session(mock_api_client):
    """Pre-configured SDK session for unit tests."""
    callbacks = ChatCallbacks()
    config = ChatConfig(debug_mode=True)
    session = ChatSession(callbacks=callbacks, config=config)
    session.client = mock_api_client
    return session


@pytest.fixture
def integration_session(test_credentials):
    """
    Pre-configured SDK session for integration tests.
    
    Skips test if credentials not available.
    """
    if not test_credentials:
        pytest.skip("Test credentials not available. Set TEST_SERVICE_ACCOUNT_API_KEY and TEST_PLAYER_FEDERATED_ID")
    
    callbacks = ChatCallbacks()
    config = ChatConfig(debug_mode=True)
    session = ChatSession(callbacks=callbacks, config=config)
    return session


def create_test_audio_data(duration_seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    """
    Create test audio data (sine wave).
    
    Args:
        duration_seconds: Duration of audio
        sample_rate: Sample rate
        
    Returns:
        Raw PCM audio data as bytes
    """
    import math
    
    num_samples = int(duration_seconds * sample_rate)
    audio_data = []
    
    for i in range(num_samples):
        # Generate sine wave sample
        sample = int(32767 * 0.5 * math.sin(2 * math.pi * 440.0 * i / sample_rate))
        # Convert to 16-bit signed integer bytes
        audio_data.append(sample.to_bytes(2, byteorder='little', signed=True))
    
    return b''.join(audio_data)


def verify_chat_response(response, expect_text: bool = False, expect_audio: bool = False):
    """
    Verify a ChatResponse object.
    
    Args:
        response: ChatResponse object to verify
        expect_text: Whether text is expected
        expect_audio: Whether audio is expected
    """
    assert response is not None
    assert hasattr(response, 'text')
    assert hasattr(response, 'audio')
    assert hasattr(response, 'transcription')
    assert hasattr(response, 'error')
    
    if expect_text:
        assert response.text, "Expected text response"
    if expect_audio:
        assert response.audio, "Expected audio response"
    
    if response.error:
        raise response.error
