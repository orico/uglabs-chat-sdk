"""Command-line chat interface for UG Game."""

import asyncio
from typing import List, Optional
import os
import pathlib

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console

from ..api.client import UGGameClient, UGGameAPIError
from ..core.config import settings
from ..core.voice import record_voice_input_async, play_audio_response_async, generate_test_audio


class ChatSession:
    """Manages chat session state and history."""

    def __init__(self):
        self.client = UGGameClient()
        self.console = Console()
        self.message_history: List[str] = []
        self.history_index = -1
        self.is_connected = False
        self.voice_mode = True  # Default to voice conversation mode
        self.debug_mode = False  # Default to debug logs off
        self.audio_output = False  # Default to no audio output

        # Use permanent history file in project root (.ug_game/chat_history)
        # This persists across application restarts
        project_root = pathlib.Path(__file__).parent.parent.parent.parent  # Go up to project root
        history_dir = project_root / ".ug_game"
        history_dir.mkdir(exist_ok=True)
        history_file = history_dir / "chat_history"

        self.prompt_history = FileHistory(str(history_file))
        # Voice command handling
        self.pending_voice_command: Optional[int] = None  # Duration in seconds

    async def initialize(self) -> None:
        """Initialize the chat session."""
        try:
            if not settings.service_account_api_key or not settings.player_federated_id:
                raise UGGameAPIError(
                    "Missing API credentials. Please set SERVICE_ACCOUNT_API_KEY and PLAYER_FEDERATED_ID"
                )

            # Authenticate player
            self.console.print("[green]Authenticating...[/green]")
            await self.client.authenticate_player(
                settings.service_account_api_key.get_secret_value(),
                settings.player_federated_id
            )
            self.console.print("[green]✓ Authentication successful[/green]")

            # Connect to WebSocket
            self.console.print("[green]Connecting to chat service...[/green]")
            await self.client.connect()
            self.console.print("[green]✓ Connected[/green]")

            # Authenticate WebSocket
            await self.client.authenticate_websocket()
            self.console.print("[green]✓ WebSocket authenticated[/green]")

            # Set configuration
            await self.client.set_configuration({"prompt": settings.default_prompt})
            self.console.print("[green]✓ Configuration set[/green]")

            self.is_connected = True
            mode_indicator = "VOICE CONVERSATION" if self.voice_mode else "TEXT CHAT"
            mode_color = "green" if self.voice_mode else "blue"
            mode_instructions = "Press Enter to start voice recording" if self.voice_mode else "Type your message or use commands"

            self.console.print(f"[bold {mode_color}]Chat ready in {mode_indicator} mode![/bold {mode_color}]")
            self.console.print(f"[dim]{mode_instructions}:[/dim]")

            # Check if running interactively and show relevant message
            import sys
            is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
            if self.voice_mode and not is_interactive:
                self.console.print("[dim]Note: Voice recording requires interactive terminal with microphone access[/dim]")
            self.console.print("[dim]/help - Show all commands[/dim]")
            self.console.print("[dim]/voice [sec] - Record voice message (default 3s)[/dim]")
            self.console.print("[dim]/test-audio - Test audio playback[/dim]")
            self.console.print("[dim]/toggle-voice - Switch conversation modes[/dim]")
            self.console.print("[dim]/audio-info - Show audio device info[/dim]")
            self.console.print("[dim]/audio-output - Toggle audio output on/off[/dim]")
            self.console.print("[dim]/system <prompt> - Update system prompt[/dim]")
            self.console.print("[dim]/new <id> - Create new player[/dim]")
            self.console.print("[dim]/status - Show connection status[/dim]")
            self.console.print("[dim]/debug - Toggle debug logging on/off[/dim]")
            self.console.print("[dim]/quit - Exit chat[/dim]")
            self.console.print()
            self.console.print("[dim]💡 Use ↑/↓ arrows for persistent message history, Tab for auto-completion[/dim]")
            self.console.print()

        except UGGameAPIError as e:
            self.console.print(f"[red]Error initializing chat: {e}[/red]")
            raise

    async def create_new_player(self, external_id: str) -> str:
        """Create a new player and return federated_id."""
        if not settings.developer_api_key:
            raise UGGameAPIError("DEVELOPER_API_KEY not set. Cannot create new player.")

        try:
            player_data = await self.client.create_player(
                settings.developer_api_key.get_secret_value(),
                external_id
            )
            federated_id = player_data["federated_id"]
            self.console.print(f"[green]✓ Created new player: {federated_id}[/green]")
            return federated_id
        except UGGameAPIError as e:
            self.console.print(f"[red]Error creating player: {e}[/red]")
            raise

    async def update_system_prompt(self, new_prompt: str) -> None:
        """Update the system prompt for the AI."""
        if not self.is_connected:
            self.console.print("[red]Not connected. Please restart the chat.[/red]")
            return

        try:
            self.console.print("[dim]Updating system prompt...[/dim]")
            await self.client.set_configuration({"prompt": new_prompt})
            self.console.print("[green]✓ System prompt updated[/green]")
        except UGGameAPIError as e:
            self.console.print(f"[red]Error updating system prompt: {e}[/red]")

    async def send_message(self, text: str) -> None:
        """Send a message and display the response."""
        if not self.is_connected:
            self.console.print("[red]Not connected. Please restart the chat.[/red]")
            return

        try:
            # Send message and collect responses
            text_responses = []
            audio_responses = []
            response_count = 0

            if self.debug_mode:
                self.console.print("[dim]Debug: Sending text message to API...[/dim]")
            async for response in self.client.send_text_interaction(text, audio_output=self.audio_output):
                response_count += 1
                if self.debug_mode:
                    self.console.print(f"[dim]Debug: Text response {response_count}: {response}[/dim]")

                if response.get("event") == "text":
                    text_responses.append(response.get("text", ""))
                elif response.get("event") == "audio":
                    audio_responses.append(response.get("audio", b""))

            # Display text response if available
            if text_responses:
                full_response = "".join(text_responses)
                self.console.print(f"[bold green]AI:[/bold green] {full_response}")
                self.message_history.append(text)
            else:
                self.console.print("[yellow]No response received[/yellow]")
                if self.debug_mode:
                    self.console.print("[dim]Debug: No text responses collected[/dim]")

            # Play audio response if available and audio output is enabled
            if audio_responses and self.audio_output:
                if self.debug_mode:
                    total_bytes = sum(len(chunk) if isinstance(chunk, (bytes, str)) else 0 for chunk in audio_responses)
                    self.console.print(f"[dim]Debug: Collected {len(audio_responses)} audio chunks ({total_bytes} bytes total), processing and merging before playback[/dim]")
                # Process audio responses - handle base64 strings and decode MP3/WAV to PCM
                processed_audio_chunks = []
                for i, audio_data in enumerate(audio_responses, 1):
                    if isinstance(audio_data, str):
                        # Decode base64 string to bytes
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                    else:
                        # Already bytes
                        audio_bytes = audio_data

                    if self.debug_mode:
                        self.console.print(f"[dim]Debug: Processing audio chunk {i}/{len(audio_responses)}: {len(audio_bytes)} bytes, starts with: {audio_bytes[:10].hex() if len(audio_bytes) >= 10 else audio_bytes.hex()}[/dim]")

                    # Check if this looks like MP3 data (ID3 header or MP3 frame sync)
                    is_mp3_like = False
                    if len(audio_bytes) >= 3 and audio_bytes[:3] == b'ID3':
                        is_mp3_like = True
                        if self.debug_mode:
                            self.console.print(f"[dim]Debug: Chunk {i} has ID3 header - MP3 file[/dim]")
                    elif len(audio_bytes) >= 2 and audio_bytes[:2] in [b'\xff\xfb', b'\xff\xf3', b'\xff\xfa', b'\xff\xf2']:
                        is_mp3_like = True
                        if self.debug_mode:
                            self.console.print(f"[dim]Debug: Chunk {i} starts with MP3 frame sync - treating as MP3[/dim]")

                    if is_mp3_like:
                        # Try to decode as MP3
                        try:
                            from pydub import AudioSegment
                            import io

                            # Load MP3 from bytes
                            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

                            # Convert to raw PCM bytes (16-bit, mono, 16kHz to match our player)
                            pcm_data = audio_segment.set_frame_rate(16000).set_channels(1).raw_data
                            processed_audio_chunks.append(pcm_data)
                            if self.debug_mode:
                                self.console.print(f"[dim]Debug: Chunk {i} decoded as MP3: {len(pcm_data)} bytes PCM[/dim]")
                        except ImportError:
                            if self.debug_mode:
                                self.console.print("[red]MP3 decoding not available - install pydub and ffmpeg[/red]")
                        except Exception as e:
                            if self.debug_mode:
                                self.console.print(f"[red]MP3 decode error on chunk {i}: {e}[/red]")
                            # If MP3 decoding fails, don't skip - try as raw data instead
                            if len(audio_bytes) > 0 and len(audio_bytes) % 2 == 0:
                                processed_audio_chunks.append(audio_bytes)
                                if self.debug_mode:
                                    self.console.print(f"[yellow]Debug: Chunk {i} MP3 decode failed, treating as raw PCM: {len(audio_bytes)} bytes[/yellow]")
                            else:
                                if self.debug_mode:
                                    self.console.print(f"[yellow]Debug: Skipping chunk {i} - MP3 decode failed and invalid length[/yellow]")
                    elif len(audio_bytes) > 44 and audio_bytes[:4] == b'RIFF':
                        # WAV file - extract PCM data (skip WAV header)
                        pcm_data = audio_bytes[44:]  # Skip 44-byte WAV header
                        processed_audio_chunks.append(pcm_data)
                        if self.debug_mode:
                            self.console.print(f"[dim]Debug: Chunk {i} processed as WAV: {len(pcm_data)} bytes PCM[/dim]")
                    elif len(audio_bytes) > 0:
                        # Check if it looks like valid PCM data (should be even length for 16-bit audio)
                        if len(audio_bytes) % 2 == 0:
                            # Assume raw PCM data
                            processed_audio_chunks.append(audio_bytes)
                            if self.debug_mode:
                                self.console.print(f"[dim]Debug: Chunk {i} treated as raw PCM: {len(audio_bytes)} bytes[/dim]")
                        else:
                            if self.debug_mode:
                                self.console.print(f"[yellow]Debug: Skipping chunk {i} - odd length {len(audio_bytes)} bytes, not valid PCM[/yellow]")
                    else:
                        if self.debug_mode:
                            self.console.print(f"[yellow]Debug: Skipping chunk {i} - empty data[/yellow]")

                if processed_audio_chunks:
                    # Combine all audio chunks if multiple
                    combined_audio = b''.join(processed_audio_chunks)

                    # Ensure PCM data is properly aligned (multiple of 2 for 16-bit audio)
                    if len(combined_audio) % 2 != 0:
                        combined_audio = combined_audio[:-1]  # Remove last byte if odd length

                    if self.debug_mode:
                        self.console.print(f"[dim]Debug: Combined audio: {len(combined_audio)} bytes PCM data, playing now...[/dim]")

                    await play_audio_response_async(combined_audio)

        except UGGameAPIError as e:
            self.console.print(f"[red]Error sending message: {e}[/red]")

    async def send_voice_message(self, duration_seconds: int = 5) -> None:
        """Record and send voice message."""
        if not self.is_connected:
            self.console.print("[red]Not connected. Please restart the chat.[/red]")
            return

        try:
            # Record voice input
            self.console.print(f"[bold blue]Recording voice for {duration_seconds} seconds...[/bold blue]")
            audio_data = await record_voice_input_async(duration_seconds=duration_seconds, debug_mode=self.debug_mode)

            if not audio_data:
                self.console.print("[yellow]No audio recorded[/yellow]")
                return

            # Analyze audio quality and check for silence
            try:
                import numpy as np
                # Check if this is WAV data (starts with 'RIFF') or raw PCM
                if len(audio_data) > 44 and audio_data[:4] == b'RIFF':
                    # WAV file - extract PCM data (skip WAV header)
                    pcm_data = audio_data[44:]  # Skip 44-byte WAV header
                    audio_array = np.frombuffer(pcm_data, dtype=np.int16)
                else:
                    # Raw PCM data
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)

                if len(audio_array) > 0:
                    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                    silence_threshold = 50  # Lower threshold for detecting very quiet audio

                    if rms < silence_threshold:
                        import sys
                        is_interactive = sys.stdin.isatty() and sys.stdout.isatty()

                        if is_interactive:
                            self.console.print(f"[yellow]No speech detected (RMS: {rms:.1f}) - please speak clearly and try again[/yellow]")
                        else:
                            self.console.print(f"[yellow]No audio input available (RMS: {rms:.1f}) - running in non-interactive mode[/yellow]")
                            self.console.print(f"[yellow]Voice recording requires an interactive terminal session with microphone access[/yellow]")
                        return  # Exit early without making API calls
                    else:
                        self.console.print(f"[dim]Audio RMS level: {rms:.1f} (good quality)[/dim]")
                else:
                    self.console.print("[yellow]No audio data captured - please try recording again[/yellow]")
                    return  # Exit early without making API calls
            except Exception as e:
                if self.debug_mode:
                    self.console.print(f"[dim]Audio analysis error: {e}[/dim]")

            self.console.print("[bold blue]Voice recorded, processing...[/bold blue]")

            # Use UG Labs Transcription API (this is the main transcription method)
            self.console.print("[dim]Trying UG Labs Transcription API...[/dim]")

            transcribed_text = None
            try:
                # Use the correct UG Labs Transcription API with correct sample rate
                api_transcription = await self.client.send_audio_transcription(audio_data, sample_rate=16000)
                if api_transcription:
                    self.console.print(f"[green]UG API Transcribed: \"{api_transcription}\"[/green]")
                    transcribed_text = api_transcription
                else:
                    self.console.print("[yellow]UG API transcription returned empty result[/yellow]")
                    return  # Don't send to chat API if UG transcription failed
            except Exception as e:
                self.console.print(f"[yellow]UG API transcription error: {e}[/yellow]")
                return  # Don't send to chat API if UG transcription failed

            if not transcribed_text:
                self.console.print("[yellow]UG transcription failed - not sending to chat API[/yellow]")
                return

            # Disconnect and reconnect to ensure clean WebSocket state - this is a hack! 
            # TODO: Find a better way to do this.
            self.console.print("[dim]Reconnecting WebSocket for clean text interaction...[/dim]")
            await self.client.disconnect()
            await self.client.connect()
            await self.client.authenticate_websocket()
            await self.client.set_configuration({"prompt": settings.default_prompt})

            # Send UG transcribed text to API for chat response
            text_responses = []
            audio_responses = []  # For future audio response handling

            if self.debug_mode:
                self.console.print(f"[dim]DEBUG: Sending text interaction: '{transcribed_text}'[/dim]")

            try:
                async with asyncio.timeout(10.0):  # 3 second timeout for text interaction
                    response_count = 0
                    async for response in self.client.send_text_interaction(transcribed_text, audio_output=self.audio_output):
                        response_count += 1
                        if self.debug_mode:
                            self.console.print(f"[dim]DEBUG: Text interaction response {response_count}: {response}[/dim]")

                        if response.get("event") == "text":
                            text_responses.append(response.get("text", ""))
                        elif response.get("event") == "audio":
                            audio_responses.append(response.get("audio", b""))

                        # Check if this is the close message that ends the interaction
                        if response.get("kind") == "close":
                            if self.debug_mode:
                                self.console.print("[dim]DEBUG: Received close message, ending text interaction[/dim]")
                            break

            except asyncio.TimeoutError:
                if self.debug_mode:
                    self.console.print(f"[dim]DEBUG: Received {len(text_responses)} text responses before timeout[/dim]")
                self.console.print("[yellow]Text interaction timed out after 3 seconds[/yellow]")
                return

            # Display text response if available
            if text_responses:
                full_response = "".join(text_responses)
                self.console.print(f"[bold green]AI:[/bold green] {full_response}")

            # Play audio response if available and audio output is enabled
            if audio_responses and self.audio_output:
                if self.debug_mode:
                    total_bytes = sum(len(chunk) if isinstance(chunk, (bytes, str)) else 0 for chunk in audio_responses)
                    self.console.print(f"[dim]Debug: Collected {len(audio_responses)} voice response audio chunks ({total_bytes} bytes total), processing and merging before playback[/dim]")
                # Process audio responses - handle base64 strings and decode MP3/WAV to PCM
                processed_audio_chunks = []
                for i, audio_data in enumerate(audio_responses, 1):
                    if isinstance(audio_data, str):
                        # Decode base64 string to bytes
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                    else:
                        # Already bytes
                        audio_bytes = audio_data

                    if self.debug_mode:
                        self.console.print(f"[dim]Debug: Processing audio chunk {i}/{len(audio_responses)}: {len(audio_bytes)} bytes, starts with: {audio_bytes[:10].hex() if len(audio_bytes) >= 10 else audio_bytes.hex()}[/dim]")

                    # Check if this looks like MP3 data (ID3 header or MP3 frame sync)
                    is_mp3_like = False
                    if len(audio_bytes) >= 3 and audio_bytes[:3] == b'ID3':
                        is_mp3_like = True
                        if self.debug_mode:
                            self.console.print(f"[dim]Debug: Chunk {i} has ID3 header - MP3 file[/dim]")
                    elif len(audio_bytes) >= 2 and audio_bytes[:2] in [b'\xff\xfb', b'\xff\xf3', b'\xff\xfa', b'\xff\xf2']:
                        is_mp3_like = True
                        if self.debug_mode:
                            self.console.print(f"[dim]Debug: Chunk {i} starts with MP3 frame sync - treating as MP3[/dim]")

                    if is_mp3_like:
                        # Try to decode as MP3
                        try:
                            from pydub import AudioSegment
                            import io

                            # Load MP3 from bytes
                            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

                            # Convert to raw PCM bytes (16-bit, mono, 16kHz to match our player)
                            pcm_data = audio_segment.set_frame_rate(16000).set_channels(1).raw_data
                            processed_audio_chunks.append(pcm_data)
                            if self.debug_mode:
                                self.console.print(f"[dim]Debug: Chunk {i} decoded as MP3: {len(pcm_data)} bytes PCM[/dim]")
                        except ImportError:
                            if self.debug_mode:
                                self.console.print("[red]MP3 decoding not available - install pydub and ffmpeg[/red]")
                        except Exception as e:
                            if self.debug_mode:
                                self.console.print(f"[red]MP3 decode error on chunk {i}: {e}[/red]")
                            # If MP3 decoding fails, don't skip - try as raw data instead
                            if len(audio_bytes) > 0 and len(audio_bytes) % 2 == 0:
                                processed_audio_chunks.append(audio_bytes)
                                if self.debug_mode:
                                    self.console.print(f"[yellow]Debug: Chunk {i} MP3 decode failed, treating as raw PCM: {len(audio_bytes)} bytes[/yellow]")
                            else:
                                if self.debug_mode:
                                    self.console.print(f"[yellow]Debug: Skipping chunk {i} - MP3 decode failed and invalid length[/yellow]")
                    elif len(audio_bytes) > 44 and audio_bytes[:4] == b'RIFF':
                        # WAV file - extract PCM data (skip WAV header)
                        pcm_data = audio_bytes[44:]  # Skip 44-byte WAV header
                        processed_audio_chunks.append(pcm_data)
                        if self.debug_mode:
                            self.console.print(f"[dim]Debug: Chunk {i} processed as WAV: {len(pcm_data)} bytes PCM[/dim]")
                    elif len(audio_bytes) > 0:
                        # Check if it looks like valid PCM data (should be even length for 16-bit audio)
                        if len(audio_bytes) % 2 == 0:
                            # Assume raw PCM data
                            processed_audio_chunks.append(audio_bytes)
                            if self.debug_mode:
                                self.console.print(f"[dim]Debug: Chunk {i} treated as raw PCM: {len(audio_bytes)} bytes[/dim]")
                        else:
                            if self.debug_mode:
                                self.console.print(f"[yellow]Debug: Skipping chunk {i} - odd length {len(audio_bytes)} bytes, not valid PCM[/yellow]")
                    else:
                        if self.debug_mode:
                            self.console.print(f"[yellow]Debug: Skipping chunk {i} - empty data[/yellow]")

                if processed_audio_chunks:
                    # Combine all audio chunks if multiple
                    combined_audio = b''.join(processed_audio_chunks)

                    # Ensure PCM data is properly aligned (multiple of 2 for 16-bit audio)
                    if len(combined_audio) % 2 != 0:
                        combined_audio = combined_audio[:-1]  # Remove last byte if odd length

                    if self.debug_mode:
                        self.console.print(f"[dim]Debug: Combined voice audio: {len(combined_audio)} bytes PCM data, playing now...[/dim]")

                    await play_audio_response_async(combined_audio)

            # Add to message history
            voice_message = f"[Voice: {transcribed_text if transcribed_text else 'audio'}]"
            self.message_history.append(voice_message)

        except UGGameAPIError as e:
            self.console.print(f"[red]Error sending voice message: {e}[/red]")
        except Exception as e:
            self.console.print(f"[red]Voice processing error: {e}[/red]")

    async def cleanup(self) -> None:
        """Clean up the chat session."""
        if self.client:
            await self.client.disconnect()
        self.is_connected = False


async def async_chat_loop(session: ChatSession) -> None:
    """Fully async chat loop using prompt_toolkit's async support."""
    # Auto-completion for commands
    commands = ['/quit', '/exit', '/new', '/help', '/status', '/voice', '/test-audio', '/system', '/toggle-voice', '/debug', '/audio-info', '/audio-output']
    completer = WordCompleter(commands, ignore_case=True)

    # Create prompt session with history and completion
    prompt_session = PromptSession(
        history=session.prompt_history,
        completer=completer,
        complete_while_typing=True,
        complete_in_thread=True,  # Enable completion in background thread
        reserve_space_for_menu=4,  # Reserve space for completion menu
    )

    try:
        # Initialize session
        await session.initialize()

        while True:
            try:
                # Get user input with history support (async)
                if session.voice_mode:
                    prompt_text = "🎤 Press Enter to record voice\n> "
                else:
                    prompt_text = "You>"
                user_input = await prompt_session.prompt_async(prompt_text)

                # Handle voice mode: empty input triggers voice recording
                if session.voice_mode and not user_input.strip():
                    try:
                        await session.send_voice_message(3)  # Default 3 seconds
                    except Exception as e:
                        session.console.print(f"[red]Voice recording failed: {e}[/red]")
                    continue

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    command_line = user_input[1:].strip()
                    command_parts = command_line.split()
                    command = command_parts[0].lower() if command_parts else ""

                    if command == "quit" or command == "exit":
                        break
                    elif command == "help":
                        session.console.print("[bold]Available commands:[/bold]")
                        session.console.print("  /help           - Show this help message")
                        session.console.print("  /new <id>       - Create a new player with external ID")
                        session.console.print("  /voice [sec]    - Record and send voice message (default 3 seconds)")
                        session.console.print("  /test-audio     - Play test audio tone to verify playback")
                        session.console.print("  /toggle-voice   - Switch between voice and text conversation modes")
                        session.console.print("  /status         - Show connection status")
                        session.console.print("  /system <prompt> - Update the system prompt for the AI")
                        session.console.print("  /debug          - Toggle debug logging on/off")
                        session.console.print("  /audio-info     - Show audio device information")
                        session.console.print("  /audio-output   - Toggle audio output on/off")
                        session.console.print("  /quit           - Exit the chat")
                        session.console.print("  /exit           - Exit the chat")
                        session.console.print()
                        mode_indicator = "VOICE MODE" if session.voice_mode else "TEXT MODE"
                        mode_color = "green" if session.voice_mode else "blue"
                        session.console.print(f"[dim]Current mode: [{mode_color}]{mode_indicator}[/{mode_color}][/dim]")
                        session.console.print("[dim]Use ↑/↓ arrows for persistent message history[/dim]")
                        session.console.print("[dim]Type commands and press Tab for auto-completion[/dim]")
                        continue
                    elif command == "status":
                        status = "Connected" if session.is_connected else "Disconnected"
                        session.console.print(f"[blue]Status: {status}[/blue]")
                        if session.is_connected:
                            session.console.print(f"[blue]Message history: {len(session.message_history)} messages[/blue]")
                        continue
                    elif command == "voice":
                        # Parse optional duration parameter
                        duration = 3  # Default 3 seconds
                        if len(command_parts) > 1:
                            try:
                                duration = int(command_parts[1])
                                if duration < 1 or duration > 30:
                                    session.console.print("[red]Duration must be between 1-30 seconds[/red]")
                                    continue
                            except ValueError:
                                session.console.print("[red]Invalid duration. Use /voice or /voice <seconds>[/red]")
                                continue

                        try:
                            await session.send_voice_message(duration)
                        except Exception as e:
                            session.console.print(f"[red]Voice command failed: {e}[/red]")
                        continue
                    elif command == "test-audio":
                        # Test audio playback with a generated tone
                        try:
                            session.console.print("[dim]Generating test audio tone...[/dim]")
                            test_audio = generate_test_audio(duration_seconds=1.0, frequency=440.0)
                            session.console.print("[dim]Playing test audio (440Hz tone for 1 second)...[/dim]")
                            await play_audio_response_async(test_audio)
                            session.console.print("[dim]Test audio playback complete[/dim]")
                        except Exception as e:
                            session.console.print(f"[red]Test audio failed: {e}[/red]")
                        continue
                    elif command == "toggle-voice":
                        # Toggle between voice mode and text mode
                        session.voice_mode = not session.voice_mode
                        mode_status = "VOICE CONVERSATION" if session.voice_mode else "TEXT CONVERSATION"
                        mode_color = "green" if session.voice_mode else "blue"
                        session.console.print(f"[{mode_color}]Mode switched to: {mode_status}[/{mode_color}]")
                        if session.voice_mode:
                            session.console.print("[green]Press Enter to start voice recording[/green]")
                        else:
                            session.console.print("[blue]Type messages normally[/blue]")
                        continue
                    elif command == "system":
                        # Parse the new system prompt
                        if len(command_parts) < 2:
                            session.console.print("[red]Usage: /system <new_system_prompt>[/red]")
                            session.console.print("[dim]Example: /system You are a helpful coding assistant[/dim]")
                            continue

                        new_prompt = " ".join(command_parts[1:])  # Join all remaining parts as the prompt
                        try:
                            await session.update_system_prompt(new_prompt)
                        except Exception as e:
                            session.console.print(f"[red]System command failed: {e}[/red]")
                        continue
                    elif command == "new":
                        # Parse external_id from command
                        if len(command_parts) < 2:
                            session.console.print("[red]Usage: /new <external_id>[/red]")
                            continue

                        external_id = command_parts[1]
                        try:
                            federated_id = await session.create_new_player(external_id)
                            session.console.print(f"[green]New player federated_id: {federated_id}[/green]")
                        except UGGameAPIError:
                            pass
                        continue
                    elif command == "debug":
                        # Toggle debug mode
                        session.debug_mode = not session.debug_mode
                        debug_status = "ENABLED" if session.debug_mode else "DISABLED"
                        mode_color = "yellow" if session.debug_mode else "dim"
                        session.console.print(f"[{mode_color}]Debug logging {debug_status}[/{mode_color}]")
                        continue
                    elif command == "audio-output":
                        # Toggle audio output
                        session.audio_output = not session.audio_output
                        audio_status = "ENABLED" if session.audio_output else "DISABLED"
                        mode_color = "green" if session.audio_output else "dim"
                        session.console.print(f"[{mode_color}]Audio output {audio_status}[/{mode_color}]")
                        continue
                    elif command == "audio-info":
                        # Show audio device information
                        try:
                            import pyaudio
                            p = pyaudio.PyAudio()
                            session.console.print("[bold]Available Audio Devices:[/bold]")

                            for i in range(p.get_device_count()):
                                info = p.get_device_info_by_index(i)
                                name = info.get("name", "Unknown")
                                inputs = info.get("maxInputChannels", 0)
                                outputs = info.get("maxOutputChannels", 0)
                                default_sample_rate = info.get("defaultSampleRate", 0)

                                if inputs > 0:
                                    session.console.print(f"[green]🎤 {i}: {name} (Input: {inputs}ch, {default_sample_rate}Hz)[/green]")
                                elif outputs > 0:
                                    session.console.print(f"[blue]🔊 {i}: {name} (Output: {outputs}ch)[/blue]")
                                else:
                                    session.console.print(f"[dim]   {i}: {name}[/dim]")

                            # Check if running interactively
                            import sys
                            is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
                            if not is_interactive:
                                session.console.print("[yellow]⚠️  Note: Running in non-interactive mode[/yellow]")
                                session.console.print("[yellow]   Voice recording will show RMS 0.0 (no microphone access)[/yellow]")
                                session.console.print("[yellow]   Run 'python run_chat.py' in an interactive terminal for real voice input[/yellow]")
                            else:
                                session.console.print("[green]✅ Interactive mode detected - microphone should work[/green]")

                            p.terminate()
                        except Exception as e:
                            session.console.print(f"[red]Error getting audio info: {e}[/red]")
                        continue
                    else:
                        session.console.print(f"[red]Unknown command: {command}[/red]")
                        session.console.print("[dim]Type /help for available commands[/dim]")
                        continue

                # Send regular message
                await session.send_message(user_input)

            except KeyboardInterrupt:
                break
            except EOFError:
                break

    finally:
        await session.cleanup()


def sync_chat_loop(session: ChatSession) -> None:
    """Synchronous wrapper for async chat loop."""
    asyncio.run(async_chat_loop(session))


async def chat_loop(session: ChatSession) -> None:
    """Main chat loop - runs async chat loop directly."""
    await async_chat_loop(session)


@click.command()
@click.option(
    "--player-id",
    help="Player federated ID to use for chat",
    envvar="PLAYER_FEDERATED_ID"
)
def main(player_id: Optional[str]) -> None:
    """Start the UG Game chat interface."""
    console = Console()

    # Override player ID if provided
    if player_id:
        settings.player_federated_id = player_id

    console.print("[bold]UG Labs PUG Chat Interface[/bold]")
    console.print("=" * 40)

    # Check required settings
    if not settings.service_account_api_key:
        console.print("[red]Error: SERVICE_ACCOUNT_API_KEY not set[/red]")
        console.print("Please set it in your .env file or environment variables")
        return

    if not settings.player_federated_id:
        console.print("[red]Error: PLAYER_FEDERATED_ID not set[/red]")
        console.print("Please set it in your .env file or use --player-id")
        console.print("Or run with /new command to create a new player")
        return

    session = ChatSession()

    try:
        asyncio.run(chat_loop(session))
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
    finally:
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    main()