"""MCP Tools for UG Game text and voice interactions."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..ug_game.sdk import ChatCallbacks, ChatConfig, ChatResponse, ChatSession


class TextChatTool(BaseModel):
    """Tool for sending text messages to the UG Game AI."""

    message: str = Field(..., description="The text message to send to the AI")
    audio_output: bool = Field(
        default=False, description="Whether to request audio output from the AI"
    )


class VoiceChatTool(BaseModel):
    """Tool for recording and sending voice messages to the UG Game AI."""

    duration_seconds: int = Field(
        default=3, description="Duration in seconds to record voice input", ge=1, le=10
    )


class UGGameTools:
    """Handles UG Game SDK interactions for MCP tools."""

    def __init__(self):
        self.chat_session: Optional[ChatSession] = None
        self.is_initialized = False

    async def initialize(
        self,
        service_account_api_key: str,
        player_federated_id: str,
        system_prompt: Optional[str] = None,
        config: Optional[ChatConfig] = None,
    ) -> None:
        """Initialize the chat session."""
        if self.chat_session:
            await self.chat_session.disconnect()

        # Create callbacks for MCP integration
        callbacks = ChatCallbacks(
            on_text_response=self._on_text_response,
            on_audio_response=self._on_audio_response,
            on_error=self._on_error,
            on_status_change=self._on_status_change,
        )

        self.chat_session = ChatSession(callbacks=callbacks, config=config or ChatConfig())

        try:
            await self.chat_session.initialize(
                service_account_api_key=service_account_api_key,
                player_federated_id=player_federated_id,
                system_prompt=system_prompt,
            )
            self.is_initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize chat session: {e}") from None

    async def cleanup(self) -> None:
        """Clean up the chat session."""
        if self.chat_session:
            await self.chat_session.disconnect()
            self.chat_session = None
        self.is_initialized = False

    def _on_text_response(self, text: str) -> None:
        """Handle text response callback."""
        # In MCP context, we'll handle this in the tool response
        pass

    def _on_audio_response(self, audio: bytes) -> None:
        """Handle audio response callback."""
        # In MCP context, we'll handle this in the tool response
        pass

    def _on_error(self, error: Exception) -> None:
        """Handle error callback."""
        # In MCP context, we'll handle this in the tool response
        pass

    def _on_status_change(self, status: str) -> None:
        """Handle status change callback."""
        # In MCP context, we'll handle this in the tool response
        pass

    async def send_text_message(self, tool: TextChatTool) -> Dict[str, Any]:
        """Send a text message and return the response."""
        if not self.is_initialized or not self.chat_session:
            raise RuntimeError("Chat session not initialized. Call initialize() first.")

        try:
            response: ChatResponse = await self.chat_session.send_text(
                text=tool.message, audio_output=tool.audio_output
            )

            if response.error:
                return {"error": str(response.error), "success": False}

            result = {"text": response.text, "has_audio": response.has_audio, "success": True}

            if response.has_audio:
                result["audio_size"] = len(response.audio) if response.audio else 0

            return result

        except Exception as e:
            return {"error": f"Failed to send text message: {str(e)}", "success": False}

    async def send_voice_message(self, tool: VoiceChatTool) -> Dict[str, Any]:
        """Record and send a voice message, return the response."""
        if not self.is_initialized or not self.chat_session:
            raise RuntimeError("Chat session not initialized. Call initialize() first.")

        try:
            response: ChatResponse = await self.chat_session.record_and_send_voice(
                duration_seconds=tool.duration_seconds
            )

            if response.error:
                return {"error": str(response.error), "success": False}

            result = {
                "text": response.text,
                "transcription": response.transcription,
                "has_audio": response.has_audio,
                "success": True,
            }

            if response.has_audio:
                result["audio_size"] = len(response.audio) if response.audio else 0

            return result

        except Exception as e:
            return {"error": f"Failed to send voice message: {str(e)}", "success": False}
