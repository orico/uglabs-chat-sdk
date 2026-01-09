"""SDK ChatSession - CLI-agnostic chat interface."""

import asyncio
import base64
import io
from typing import List, Optional

import numpy as np
from pydub import AudioSegment

from ..api.client import UGGameClient, UGGameAPIError
from ..core.config import settings
from ..core.voice import (
    record_voice_input_async,
    play_audio_response_async,
    transcribe_audio_local_async,
)
from .types import ChatResponse, ChatCallbacks, ChatConfig


def _process_audio_chunks(audio_responses: List, debug_mode: bool = False) -> bytes:
    """Process audio response chunks and convert to PCM format."""
    processed_audio_chunks = []
    
    for i, audio_data in enumerate(audio_responses, 1):
        if isinstance(audio_data, str):
            # Decode base64 string to bytes
            audio_bytes = base64.b64decode(audio_data)
        else:
            # Already bytes
            audio_bytes = audio_data

        if debug_mode:
            print(f"Debug: Processing audio chunk {i}/{len(audio_responses)}: {len(audio_bytes)} bytes")

        # Check if this looks like MP3 data (ID3 header or MP3 frame sync)
        is_mp3_like = False
        if len(audio_bytes) >= 3 and audio_bytes[:3] == b'ID3':
            is_mp3_like = True
        elif len(audio_bytes) >= 2 and audio_bytes[:2] in [b'\xff\xfb', b'\xff\xf3', b'\xff\xfa', b'\xff\xf2']:
            is_mp3_like = True

        if is_mp3_like:
            # Try to decode as MP3
            try:
                # Load MP3 from bytes
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                # Convert to raw PCM bytes (16-bit, mono, 16kHz)
                pcm_data = audio_segment.set_frame_rate(16000).set_channels(1).raw_data
                processed_audio_chunks.append(pcm_data)
            except ImportError:
                if debug_mode:
                    print("MP3 decoding not available - install pydub and ffmpeg")
            except Exception as e:
                if debug_mode:
                    print(f"MP3 decode error on chunk {i}: {e}")
                # If MP3 decoding fails, try as raw data instead
                if len(audio_bytes) > 0 and len(audio_bytes) % 2 == 0:
                    processed_audio_chunks.append(audio_bytes)
        elif len(audio_bytes) > 44 and audio_bytes[:4] == b'RIFF':
            # WAV file - extract PCM data (skip WAV header)
            pcm_data = audio_bytes[44:]  # Skip 44-byte WAV header
            processed_audio_chunks.append(pcm_data)
        elif len(audio_bytes) > 0:
            # Check if it looks like valid PCM data (should be even length for 16-bit audio)
            if len(audio_bytes) % 2 == 0:
                # Assume raw PCM data
                processed_audio_chunks.append(audio_bytes)

    if processed_audio_chunks:
        # Combine all audio chunks if multiple
        combined_audio = b''.join(processed_audio_chunks)
        # Ensure PCM data is properly aligned (multiple of 2 for 16-bit audio)
        if len(combined_audio) % 2 != 0:
            combined_audio = combined_audio[:-1]  # Remove last byte if odd length
        return combined_audio
    
    return b''


class ChatSession:
    """SDK ChatSession - CLI-agnostic chat interface with callbacks."""

    def __init__(
        self,
        callbacks: Optional[ChatCallbacks] = None,
        config: Optional[ChatConfig] = None,
    ):
        """
        Initialize a new chat session.

        Args:
            callbacks: Optional callbacks for events
            config: Optional configuration override
        """
        self.client = UGGameClient()
        self.callbacks = callbacks or ChatCallbacks()
        self.config = config or ChatConfig()
        self.message_history: List[str] = []
        self.is_connected = False
        self.system_prompt: Optional[str] = None

        # Override client URLs if config provides them
        if self.config.api_base_url:
            settings.api_base_url = self.config.api_base_url
        if self.config.websocket_url:
            settings.websocket_url = self.config.websocket_url

    async def initialize(
        self,
        service_account_api_key: str,
        player_federated_id: str,
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initialize the chat session.

        Args:
            service_account_api_key: Service account API key for authentication
            player_federated_id: Player federated ID
            system_prompt: Optional system prompt (uses config default if not provided)

        Raises:
            UGGameAPIError: If initialization fails
        """
        try:
            self.callbacks._call_status("Authenticating...")
            
            # Authenticate player
            await self.client.authenticate_player(
                service_account_api_key,
                player_federated_id
            )
            self.callbacks._call_status("Authentication successful")

            # Connect to WebSocket
            self.callbacks._call_status("Connecting to chat service...")
            await self.client.connect()
            self.callbacks._call_status("Connected")

            # Authenticate WebSocket
            await self.client.authenticate_websocket()
            self.callbacks._call_status("WebSocket authenticated")

            # Set configuration
            prompt = system_prompt or self.config.default_prompt or settings.default_prompt
            self.system_prompt = prompt
            await self.client.set_configuration({"prompt": prompt})
            self.callbacks._call_status("Configuration set")

            self.is_connected = True
            self.callbacks._call_status("Ready")

        except UGGameAPIError as e:
            self.callbacks._call_error(e)
            raise

    async def send_text(
        self, text: str, audio_output: bool = False
    ) -> ChatResponse:
        """
        Send a text message and get response.

        Args:
            text: Text message to send
            audio_output: Whether to request audio output

        Returns:
            ChatResponse with text and/or audio

        Raises:
            UGGameAPIError: If not connected or send fails
        """
        if not self.is_connected:
            error = UGGameAPIError("Not connected. Call initialize() first.")
            self.callbacks._call_error(error)
            raise error

        try:
            # Send message and collect responses
            text_responses = []
            audio_responses = []

            async for response in self.client.send_text_interaction(
                text, audio_output=audio_output or self.config.audio_output
            ):
                if response.get("event") == "text":
                    text_chunk = response.get("text", "")
                    text_responses.append(text_chunk)
                    # Call callback for each text chunk
                    if text_chunk:
                        self.callbacks._call_text(text_chunk)
                elif response.get("event") == "audio":
                    audio_chunk = response.get("audio", b"")
                    audio_responses.append(audio_chunk)
                    # Call callback for each audio chunk
                    if audio_chunk:
                        if isinstance(audio_chunk, str):
                            audio_bytes = base64.b64decode(audio_chunk)
                        else:
                            audio_bytes = audio_chunk
                        self.callbacks._call_audio(audio_bytes)

            # Build response
            full_text = "".join(text_responses)
            processed_audio = None

            if audio_responses:
                processed_audio = _process_audio_chunks(
                    audio_responses, debug_mode=self.config.debug_mode
                )

            response = ChatResponse(
                text=full_text,
                audio=processed_audio if processed_audio else None,
            )

            # Add to message history
            if full_text:
                self.message_history.append(text)

            return response

        except UGGameAPIError as e:
            self.callbacks._call_error(e)
            return ChatResponse(error=e)

    async def send_voice(
        self, audio_data: bytes, sample_rate: int = 16000
    ) -> ChatResponse:
        """
        Send voice audio data (already recorded).

        Args:
            audio_data: Raw PCM audio data
            sample_rate: Sample rate of audio (default 16000)

        Returns:
            ChatResponse with transcription and AI response

        Raises:
            UGGameAPIError: If not connected or send fails
        """
        if not self.is_connected:
            error = UGGameAPIError("Not connected. Call initialize() first.")
            self.callbacks._call_error(error)
            raise error

        try:
            # Transcribe audio using API
            self.callbacks._call_status("Transcribing audio...")
            transcribed_text = await self.client.send_audio_transcription(
                audio_data, sample_rate=sample_rate, language_code=self.config.language_code
            )

            if not transcribed_text:
                error = UGGameAPIError("Transcription failed - no text received")
                self.callbacks._call_error(error)
                return ChatResponse(error=error)

            # Reconnect WebSocket for clean text interaction
            # TODO: Find a better way to do this
            self.callbacks._call_status("Reconnecting WebSocket...")
            await self.client.disconnect()
            await self.client.connect()
            await self.client.authenticate_websocket()
            await self.client.set_configuration({"prompt": self.system_prompt or settings.default_prompt})

            # Send transcribed text to API
            text_responses = []
            audio_responses = []

            try:
                async with asyncio.timeout(10.0):
                    async for response in self.client.send_text_interaction(
                        transcribed_text, audio_output=self.config.audio_output
                    ):
                        if response.get("event") == "text":
                            text_chunk = response.get("text", "")
                            text_responses.append(text_chunk)
                            if text_chunk:
                                self.callbacks._call_text(text_chunk)
                        elif response.get("event") == "audio":
                            audio_chunk = response.get("audio", b"")
                            audio_responses.append(audio_chunk)
                            if audio_chunk:
                                if isinstance(audio_chunk, str):
                                    audio_bytes = base64.b64decode(audio_chunk)
                                else:
                                    audio_bytes = audio_chunk
                                self.callbacks._call_audio(audio_bytes)

                        if response.get("kind") == "close":
                            break

            except asyncio.TimeoutError:
                timeout_error = UGGameAPIError("Text interaction timed out")
                self.callbacks._call_error(timeout_error)
                return ChatResponse(error=timeout_error)

            # Build response
            full_text = "".join(text_responses)
            processed_audio = None

            if audio_responses:
                processed_audio = _process_audio_chunks(
                    audio_responses, debug_mode=self.config.debug_mode
                )

            response = ChatResponse(
                text=full_text,
                audio=processed_audio if processed_audio else None,
                transcription=transcribed_text,
            )

            # Add to message history
            voice_message = f"[Voice: {transcribed_text}]"
            self.message_history.append(voice_message)

            return response

        except UGGameAPIError as e:
            self.callbacks._call_error(e)
            return ChatResponse(error=e)

    async def record_and_send_voice(
        self, duration_seconds: int = 3
    ) -> ChatResponse:
        """
        Record voice input and send it.

        Args:
            duration_seconds: Duration to record in seconds

        Returns:
            ChatResponse with transcription and AI response
        """
        try:
            self.callbacks._call_status(f"Recording voice for {duration_seconds} seconds...")
            audio_data = await record_voice_input_async(
                duration_seconds=duration_seconds,
                debug_mode=self.config.debug_mode
            )

            if not audio_data:
                error = UGGameAPIError("No audio recorded")
                self.callbacks._call_error(error)
                return ChatResponse(error=error)

            # Check audio quality
            try:
                # Check if this is WAV data (starts with 'RIFF') or raw PCM
                if len(audio_data) > 44 and audio_data[:4] == b'RIFF':
                    pcm_data = audio_data[44:]  # Skip WAV header
                    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
                else:
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)

                if len(audio_array) > 0:
                    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                    silence_threshold = 50

                    if rms < silence_threshold:
                        error = UGGameAPIError(f"No speech detected (RMS: {rms:.1f})")
                        self.callbacks._call_error(error)
                        return ChatResponse(error=error)
            except Exception:
                pass  # Continue even if analysis fails

            # Use raw PCM data (skip WAV header if present)
            if len(audio_data) > 44 and audio_data[:4] == b'RIFF':
                pcm_data = audio_data[44:]
            else:
                pcm_data = audio_data

            return await self.send_voice(pcm_data, sample_rate=self.config.sample_rate)

        except Exception as e:
            error = UGGameAPIError(f"Voice recording failed: {e}")
            self.callbacks._call_error(error)
            return ChatResponse(error=error)

    async def update_system_prompt(self, prompt: str) -> None:
        """
        Update the system prompt for the AI.

        Args:
            prompt: New system prompt

        Raises:
            UGGameAPIError: If not connected or update fails
        """
        if not self.is_connected:
            error = UGGameAPIError("Not connected. Call initialize() first.")
            self.callbacks._call_error(error)
            raise error

        try:
            self.callbacks._call_status("Updating system prompt...")
            await self.client.set_configuration({"prompt": prompt})
            self.system_prompt = prompt
            self.callbacks._call_status("System prompt updated")
        except UGGameAPIError as e:
            self.callbacks._call_error(e)
            raise

    async def create_player(
        self, developer_api_key: str, external_id: str
    ) -> dict:
        """
        Create a new player.

        Args:
            developer_api_key: Developer API key
            external_id: External ID for the player

        Returns:
            Player data including federated_id

        Raises:
            UGGameAPIError: If creation fails
        """
        try:
            self.callbacks._call_status("Creating player...")
            player_data = await self.client.create_player(
                developer_api_key, external_id
            )
            self.callbacks._call_status("Player created")
            return player_data
        except UGGameAPIError as e:
            self.callbacks._call_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from the chat session."""
        if self.client:
            await self.client.disconnect()
        self.is_connected = False
        self.callbacks._call_status("Disconnected")

    async def cleanup(self) -> None:
        """Clean up the chat session."""
        await self.disconnect()
