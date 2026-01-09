"""Voice recording, playback, and processing utilities."""

import asyncio
import io
import os
import pathlib
import threading
import time
import wave
from datetime import datetime
from typing import Optional

import numpy as np
import pyaudio
import sounddevice as sd


class AsyncVoiceRecorder:
    """Handles voice recording from microphone using sounddevice (async-friendly)."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.recorded_frames = []

    async def record_audio(self, duration_seconds: float, debug_mode: bool = False) -> Optional[bytes]:
        """Record audio asynchronously for specified duration and return WAV data."""
        try:
            self.recorded_frames = []
            self.is_recording = True

            # Use sounddevice for better async support
            def callback(indata, frames, time, status):
                if self.is_recording and status:
                    print(f"Recording status: {status}")
                if self.is_recording:
                    self.recorded_frames.append(indata.copy())

            # Start recording in a thread to avoid blocking
            loop = asyncio.get_event_loop()

            def record_thread():
                try:
                    with sd.InputStream(
                        samplerate=self.sample_rate,
                        channels=self.channels,
                        callback=callback,
                        blocksize=1024
                    ):
                        start_time = time.time()
                        while self.is_recording and (time.time() - start_time) < duration_seconds:
                            sd.sleep(100)  # Sleep for 100ms
                except Exception as e:
                    print(f"Recording error: {e}")

            # Run recording in thread
            thread = threading.Thread(target=record_thread, daemon=True)
            thread.start()

            # Wait for duration
            await asyncio.sleep(duration_seconds)
            self.is_recording = False

            # Give thread time to finish
            await asyncio.sleep(0.1)

            if self.recorded_frames:
                # Convert numpy arrays to WAV format
                audio_array = np.concatenate(self.recorded_frames, axis=0)

                # Convert to 16-bit PCM
                audio_array = (audio_array * 32767).astype(np.int16)

                # Save to WAV file (only in debug mode)
                wav_filepath = save_wav_file(
                    audio_array.tobytes(),
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    debug_mode=debug_mode
                )
                if wav_filepath:
                    print(f"💾 Audio saved to: {wav_filepath}")

                # Create WAV file in memory for return value
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_array.tobytes())

                wav_data = wav_buffer.getvalue()
                return wav_data

            return None

        except Exception as e:
            print(f"Recording failed: {e}")
            return None

    def stop_recording(self) -> None:
        """Stop recording."""
        self.is_recording = False


class VoiceRecorder:
    """Legacy synchronous voice recorder using pyaudio."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio = None
        self.stream = None
        self.is_recording = False
        self.recorded_frames = []

    def start_recording(self) -> bool:
        """Start recording audio from microphone. Returns True if successful."""
        try:
            import pyaudio
            self.recorded_frames = []
            self.is_recording = True

            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024
            )

            def record_thread():
                try:
                    while self.is_recording:
                        data = self.stream.read(1024, exception_on_overflow=False)
                        self.recorded_frames.append(data)
                except Exception as e:
                    print(f"Recording thread error: {e}")

            thread = threading.Thread(target=record_thread, daemon=True)
            thread.start()
            return True

        except Exception as e:
            print(f"Failed to start recording: {e}")
            self.is_recording = False
            return False

    def stop_recording(self) -> Optional[bytes]:
        """Stop recording and return the recorded audio data."""
        self.is_recording = False
        time.sleep(0.1)  # Brief pause to ensure recording stops

        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()

            if self.audio:
                self.audio.terminate()

            if self.recorded_frames:
                # Combine all frames into a single bytes object
                audio_data = b''.join(self.recorded_frames)
                return audio_data

        except Exception as e:
            print(f"Error stopping recording: {e}")

        return None

    def cleanup(self) -> None:
        """Clean up audio resources."""
        try:
            if self.stream:
                self.stream.close()
            if self.audio:
                self.audio.terminate()
        except Exception:
            pass


class AudioPlayer:
    """Handles audio playback."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio = pyaudio.PyAudio()

    def play_audio_data(self, audio_data: bytes) -> None:
        """Play audio data synchronously."""
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True
            )

            # Convert bytes to numpy array for playback
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Play in chunks to avoid buffer issues
            chunk_size = 1024
            for i in range(0, len(audio_array), chunk_size):
                chunk = audio_array[i:i + chunk_size]
                stream.write(chunk.tobytes())

            stream.stop_stream()
            stream.close()

        except Exception as e:
            print(f"Playback error: {e}")

    async def play_audio_data_async(self, audio_data: bytes) -> None:
        """Play audio data asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.play_audio_data, audio_data)

    def cleanup(self) -> None:
        """Clean up audio resources."""
        self.audio.terminate()


def record_voice_input(duration_seconds: int = 5, sample_rate: int = 16000, debug_mode: bool = False) -> Optional[bytes]:
    """
    Record voice input for a specified duration.

    Args:
        duration_seconds: How long to record
        sample_rate: Audio sample rate

    Returns:
        Recorded audio data as bytes, or None if recording failed
    """
    recorder = VoiceRecorder(sample_rate=sample_rate)

    try:
        print(f"🎤 Recording for {duration_seconds} seconds... (Press Ctrl+C to stop early)")

        # Try to start recording
        if not recorder.start_recording():
            print("❌ Failed to access microphone")
            return None

        # Record for specified duration
        time.sleep(duration_seconds)

        audio_data = recorder.stop_recording()

        if audio_data:
            # Save the recorded audio as WAV file (only in debug mode)
            try:
                wav_filepath = save_wav_file(
                    audio_data,
                    sample_rate=sample_rate,
                    channels=1,  # Mono
                    debug_mode=debug_mode
                )
                print(f"✅ Recording complete ({len(audio_data)} bytes)")
                if wav_filepath:
                    print(f"💾 Audio saved to: {wav_filepath}")
            except Exception as e:
                print(f"✅ Recording complete ({len(audio_data)} bytes)")
                print(f"⚠️  Failed to save WAV file: {e}")
        else:
            print("❌ Recording failed - no data captured")

        return audio_data

    except KeyboardInterrupt:
        print("\n🛑 Recording interrupted")
        audio_data = recorder.stop_recording()
        return audio_data
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return None
    finally:
        recorder.cleanup()


async def record_voice_input_async(duration_seconds: int = 3, sample_rate: int = 16000, debug_mode: bool = False) -> Optional[bytes]:
    """
    Record voice input asynchronously using sounddevice for better reliability.

    Args:
        duration_seconds: How long to record
        sample_rate: Audio sample rate

    Returns:
        Recorded audio data as raw PCM bytes, or None if recording failed
    """
    try:
        print(f"🎤 Recording for {duration_seconds} seconds... (Press Ctrl+C to stop early)")

        # Use sounddevice directly for more reliable recording
        import sounddevice as sd

        # Set up recording parameters
        channels = 1  # Mono
        dtype = 'int16'  # 16-bit PCM

        # Record audio
        recording = sd.rec(
            int(duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype=dtype,
            device=None,  # Use default input device
            blocking=True  # Wait for recording to complete
        )

        # Wait for recording to finish (sd.rec with blocking=True waits automatically)
        print("✅ Recording complete")

        # Convert to bytes (sounddevice returns numpy array)
        audio_data = recording.tobytes()
        return audio_data

    except KeyboardInterrupt:
        print("\n🛑 Recording interrupted")
        return None
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        # Try to provide helpful error information
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [i for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]
            if input_devices:
                print(f"Available input devices: {input_devices}")
                default_input = sd.default.device[0]
                print(f"Default input device: {default_input}")
            else:
                print("No input devices found!")
        except Exception as dev_e:
            print(f"Could not query devices: {dev_e}")

        return None


def play_audio_response(audio_data: bytes, sample_rate: int = 16000) -> None:
    """
    Play audio response data.

    Args:
        audio_data: Audio data to play
        sample_rate: Audio sample rate
    """
    player = AudioPlayer(sample_rate=sample_rate)

    try:
        print("🔊 Playing audio response...")
        player.play_audio_data(audio_data)
        print("✅ Audio playback complete")
    except Exception as e:
        print(f"❌ Audio playback failed: {e}")
    finally:
        player.cleanup()


async def play_audio_response_async(audio_data: bytes, sample_rate: int = 16000) -> None:
    """
    Play audio response data asynchronously.

    Args:
        audio_data: Audio data to play
        sample_rate: Audio sample rate
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, play_audio_response, audio_data, sample_rate)


def generate_test_audio(duration_seconds: float = 1.0, frequency: float = 440.0, sample_rate: int = 16000) -> bytes:
    """
    Generate a test audio signal (sine wave) for debugging playback.

    Args:
        duration_seconds: Duration of test audio
        frequency: Frequency of sine wave in Hz
        sample_rate: Sample rate

    Returns:
        Raw PCM audio data as bytes
    """
    import math

    # Generate sine wave
    num_samples = int(duration_seconds * sample_rate)
    audio_data = []

    for i in range(num_samples):
        # Generate sine wave sample
        sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
        # Convert to 16-bit signed integer bytes
        audio_data.append(sample.to_bytes(2, byteorder='little', signed=True))

    return b''.join(audio_data)


def save_wav_file(audio_data: bytes, sample_rate: int = 16000, channels: int = 1, filename: Optional[str] = None, debug_mode: bool = False) -> Optional[str]:
    """
    Save audio data as a WAV file in the .ug_game/wav directory (only in debug mode).

    Args:
        audio_data: Raw PCM audio data
        sample_rate: Sample rate of the audio
        channels: Number of audio channels
        filename: Optional filename (will generate timestamp-based name if None)
        debug_mode: Only save WAV files when in debug mode

    Returns:
        Path to the saved WAV file, or None if not in debug mode
    """
    # Only save WAV files in debug mode
    if not debug_mode:
        return None
    # Create .ug_game/wav directory (go up to project root from src/ug_game/core/)
    project_root = pathlib.Path(__file__).parent.parent.parent.parent
    wav_dir = project_root / ".ug_game" / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voice_{timestamp}.wav"

    # Ensure .wav extension
    if not filename.lower().endswith('.wav'):
        filename += '.wav'

    filepath = wav_dir / filename

    # Convert raw PCM to numpy array and save as WAV
    audio_array = np.frombuffer(audio_data, dtype=np.int16)

    with wave.open(str(filepath), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit = 2 bytes
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_array.tobytes())

    return str(filepath)

