"""Type definitions for UG Game SDK."""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ChatResponse:
    """Response from a chat interaction."""

    text: str = ""
    audio: Optional[bytes] = None
    transcription: Optional[str] = None
    error: Optional[Exception] = None

    @property
    def has_text(self) -> bool:
        """Check if response contains text."""
        return bool(self.text)

    @property
    def has_audio(self) -> bool:
        """Check if response contains audio."""
        return self.audio is not None and len(self.audio) > 0

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return self.error is None


@dataclass
class ChatCallbacks:
    """Optional callback functions for chat events."""

    on_text_response: Optional[Callable[[str], None]] = None
    on_audio_response: Optional[Callable[[bytes], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    on_status_change: Optional[Callable[[str], None]] = None

    def _call_text(self, text: str) -> None:
        """Call text response callback if set."""
        if self.on_text_response:
            try:
                self.on_text_response(text)
            except Exception:
                pass  # Don't let callback errors break the session

    def _call_audio(self, audio: bytes) -> None:
        """Call audio response callback if set."""
        if self.on_audio_response:
            try:
                self.on_audio_response(audio)
            except Exception:
                pass  # Don't let callback errors break the session

    def _call_error(self, error: Exception) -> None:
        """Call error callback if set."""
        if self.on_error:
            try:
                self.on_error(error)
            except Exception:
                pass  # Don't let callback errors break the session

    def _call_status(self, status: str) -> None:
        """Call status change callback if set."""
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass  # Don't let callback errors break the session


@dataclass
class ChatConfig:
    """Configuration options for chat session."""

    api_base_url: Optional[str] = None
    websocket_url: Optional[str] = None
    default_prompt: Optional[str] = None
    audio_output: bool = False
    debug_mode: bool = False
    sample_rate: int = 16000
    language_code: str = "en"
