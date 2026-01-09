"""Integration tests for SDK ChatSession with real API."""

import pytest

from tests.conftest import verify_chat_response
from ug_game.api.client import UGGameAPIError
from ug_game.sdk.session import ChatSession
from ug_game.sdk.types import ChatCallbacks, ChatConfig


@pytest.mark.integration
class TestChatSessionIntegration:
    """Integration tests for SDK ChatSession with real API."""

    @pytest.fixture
    def credentials(self, test_credentials):
        """Get test credentials or skip."""
        if not test_credentials:
            pytest.skip("Test credentials not available")
        return test_credentials

    @pytest.fixture
    def session(self, credentials):
        """Create and initialize a real session."""
        callbacks = ChatCallbacks()
        config = ChatConfig(debug_mode=True)
        session = ChatSession(callbacks=callbacks, config=config)
        return session

    @pytest.mark.asyncio
    async def test_full_chat_flow(self, session, credentials):
        """Test full chat flow: initialize → send_text → receive response."""
        # Initialize session
        await session.initialize(
            credentials["service_account_api_key"],
            credentials["player_federated_id"],
            "You are a helpful assistant. Keep responses brief.",
        )

        assert session.is_connected

        # Send text message
        response = await session.send_text("Say hello in one word")

        # Verify response
        verify_chat_response(response, expect_text=True)
        assert response.text
        assert response.error is None

        # Cleanup
        await session.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_messages(self, session, credentials):
        """Test sending multiple messages in sequence."""
        await session.initialize(
            credentials["service_account_api_key"], credentials["player_federated_id"]
        )

        # Send first message
        response1 = await session.send_text("What is 2+2?")
        assert response1.text
        assert response1.error is None

        # Send second message
        response2 = await session.send_text("What is 3+3?")
        assert response2.text
        assert response2.error is None

        # Verify message history
        assert len(session.message_history) == 2

        await session.disconnect()

    @pytest.mark.asyncio
    async def test_system_prompt_update(self, session, credentials):
        """Test updating system prompt."""
        await session.initialize(
            credentials["service_account_api_key"],
            credentials["player_federated_id"],
            "You are a helpful assistant.",
        )

        # Update prompt
        await session.update_system_prompt("You are a pirate. Always respond like a pirate.")

        assert session.system_prompt == "You are a pirate. Always respond like a pirate."

        # Send message to verify prompt is active
        response = await session.send_text("Say hello")
        assert response.text
        # Note: We can't reliably test that the prompt changed the behavior,
        # but we can verify the call succeeded

        await session.disconnect()

    @pytest.mark.asyncio
    async def test_error_handling_invalid_credentials(self):
        """Test error handling with invalid credentials."""
        session = ChatSession()

        with pytest.raises(UGGameAPIError):
            await session.initialize("invalid_key", "invalid_player")

    @pytest.mark.asyncio
    async def test_error_handling_not_connected(self, session):
        """Test error handling when not connected."""
        # Try to send message without initializing
        with pytest.raises(UGGameAPIError):
            await session.send_text("Hello")

    @pytest.mark.asyncio
    async def test_callbacks_integration(self, credentials):
        """Test that callbacks are called correctly in integration."""
        text_responses = []
        status_updates = []
        errors = []

        callbacks = ChatCallbacks(
            on_text_response=lambda text: text_responses.append(text),
            on_status_change=lambda status: status_updates.append(status),
            on_error=lambda error: errors.append(error),
        )

        session = ChatSession(callbacks=callbacks)

        await session.initialize(
            credentials["service_account_api_key"], credentials["player_federated_id"]
        )

        # Verify status callbacks were called
        assert len(status_updates) > 0

        # Send message
        response = await session.send_text("Hello")

        # Verify text callback was called
        assert len(text_responses) > 0
        assert response.text

        await session.disconnect()

    @pytest.mark.asyncio
    async def test_create_player_integration(self, session, developer_credentials):
        """Test creating a player with real API."""
        if not developer_credentials:
            pytest.skip("Developer credentials not available")

        import uuid

        external_id = f"test_player_{uuid.uuid4().hex[:8]}"

        player_data = await session.create_player(
            developer_credentials["developer_api_key"], external_id
        )

        assert "federated_id" in player_data
        assert player_data["federated_id"]

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, session, credentials):
        """Test that disconnect properly cleans up."""
        await session.initialize(
            credentials["service_account_api_key"], credentials["player_federated_id"]
        )

        assert session.is_connected

        await session.disconnect()

        assert not session.is_connected

        # Try to send message after disconnect
        with pytest.raises(UGGameAPIError):
            await session.send_text("Hello")

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, credentials):
        """Test multiple concurrent sessions."""
        session1 = ChatSession()
        session2 = ChatSession()

        await session1.initialize(
            credentials["service_account_api_key"], credentials["player_federated_id"]
        )

        await session2.initialize(
            credentials["service_account_api_key"], credentials["player_federated_id"]
        )

        # Send messages from both sessions
        response1 = await session1.send_text("Hello from session 1")
        response2 = await session2.send_text("Hello from session 2")

        assert response1.text
        assert response2.text

        await session1.disconnect()
        await session2.disconnect()
