"""UG Game SDK - High-level programmatic API for chat interactions."""

from ..api.client import AuthenticationError, ConnectionError, UGGameAPIError, UGGameClient
from ..core.voice import (
    generate_test_audio,
    play_audio_response_async,
    record_voice_input_async,
)
from .session import ChatSession
from .types import ChatCallbacks, ChatConfig, ChatResponse

__all__ = [
    "ChatSession",
    "ChatResponse",
    "ChatCallbacks",
    "ChatConfig",
    "UGGameClient",
    "UGGameAPIError",
    "AuthenticationError",
    "ConnectionError",
    "record_voice_input_async",
    "play_audio_response_async",
    "generate_test_audio",
]
