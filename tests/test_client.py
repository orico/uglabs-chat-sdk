"""Tests for UG Game API client."""

import pytest
from aioresponses import aioresponses

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