"""UG Game SDK - High-level programmatic API for chat interactions."""

from .session import ChatSession
from .types import ChatResponse, ChatCallbacks, ChatConfig
from ..api.client import UGGameClient, UGGameAPIError, AuthenticationError, ConnectionError
from ..core.voice import (
    record_voice_input_async,
    play_audio_response_async,
    transcribe_audio_local_async,
    generate_test_audio,
)

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
    "transcribe_audio_local_async",
    "generate_test_audio",
]
