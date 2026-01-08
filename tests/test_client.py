"""Tests for UG Game API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ug_game.api.client import UGGameClient, UGGameAPIError


class TestUGGameClient:
    """Test cases for UGGameClient."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return UGGameClient()

    @pytest.mark.asyncio
    async def test_authenticate_player_success(self, client):
        """Test successful player authentication."""
        # Mock the aiohttp session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"access_token": "test_token"})

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.MonkeyPatch().context() as m:
            m.setattr("aiohttp.ClientSession", lambda: mock_session)

            token = await client.authenticate_player("api_key", "federated_id")

            assert token == "test_token"
            assert client.access_token == "test_token"

    @pytest.mark.asyncio
    async def test_authenticate_player_failure(self, client):
        """Test failed player authentication."""
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Invalid credentials")

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.MonkeyPatch().context() as m:
            m.setattr("aiohttp.ClientSession", lambda: mock_session)

            with pytest.raises(UGGameAPIError):
                await client.authenticate_player("api_key", "federated_id")