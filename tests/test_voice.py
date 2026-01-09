"""Tests for UG Game voice recording and playback functionality."""

import asyncio
import io
import wave
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import numpy as np
import pytest

from ug_game.core.voice import (
    AsyncVoiceRecorder,
    AudioPlayer,
    VoiceRecorder,
    generate_test_audio,
    play_audio_response,
    play_audio_response_async,
    record_voice_input,
    record_voice_input_async,
    save_wav_file,
    transcribe_audio_local,
    transcribe_audio_local_async,
)


class TestAsyncVoiceRecorder:
    """Test cases for AsyncVoiceRecorder."""

    @pytest.fixture
    def recorder(self):
        """Create a test recorder."""
        return AsyncVoiceRecorder(sample_rate=16000, channels=1)

    def test_init(self, recorder):
        """Test AsyncVoiceRecorder initialization."""
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.is_recording is False
        assert recorder.recorded_frames == []

    @pytest.mark.asyncio
    @patch('threading.Thread')
    @patch('sounddevice.InputStream')
    @patch('sounddevice.sleep')
    @patch('asyncio.sleep')
    async def test_record_audio_success(self, mock_asyncio_sleep, mock_sd_sleep, mock_input_stream, mock_thread, recorder):
        """Test successful audio recording."""
        # Mock the input stream context manager
        mock_stream = MagicMock()
        mock_input_stream.return_value.__enter__.return_value = mock_stream
        mock_input_stream.return_value.__exit__.return_value = None

        # Mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Simulate that frames were recorded by setting them after "recording"
        test_frames = [np.array([0.1, 0.2, 0.3]), np.array([0.4, 0.5, 0.6])]

        # Mock the thread to set frames after sleep
        def set_frames_after_sleep(*args, **kwargs):
            recorder.recorded_frames = test_frames

        mock_asyncio_sleep.side_effect = set_frames_after_sleep

        with patch('ug_game.core.voice.save_wav_file', return_value=None):
            result = await recorder.record_audio(duration_seconds=0.1)

        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    @patch('sounddevice.InputStream')
    @patch('asyncio.sleep')
    async def test_record_audio_no_frames(self, mock_asyncio_sleep, mock_input_stream, recorder):
        """Test audio recording with no frames recorded."""
        # Mock the input stream context manager
        mock_stream = MagicMock()
        mock_input_stream.return_value.__enter__.return_value = mock_stream
        mock_input_stream.return_value.__exit__.return_value = None

        # No frames recorded
        recorder.recorded_frames = []

        result = await recorder.record_audio(duration_seconds=1.0)

        assert result is None

    @pytest.mark.asyncio
    @patch('sounddevice.InputStream')
    @patch('asyncio.sleep')
    async def test_record_audio_exception(self, mock_asyncio_sleep, mock_input_stream, recorder):
        """Test audio recording with exception."""
        # Mock the input stream to raise an exception
        mock_input_stream.side_effect = Exception("Recording failed")

        result = await recorder.record_audio(duration_seconds=1.0)

        assert result is None


class TestVoiceRecorder:
    """Test cases for VoiceRecorder."""

    @pytest.fixture
    def recorder(self):
        """Create a test recorder."""
        return VoiceRecorder()

    def test_init(self, recorder):
        """Test VoiceRecorder initialization."""
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.audio is None
        assert recorder.stream is None
        assert recorder.is_recording is False
        assert recorder.recorded_frames == []

    @patch('pyaudio.PyAudio')
    def test_start_recording_success(self, mock_pyaudio, recorder):
        """Test successful recording start."""
        # Mock PyAudio and stream
        mock_pa = MagicMock()
        mock_pyaudio.return_value = mock_pa

        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream

        result = recorder.start_recording()

        assert result is True
        assert recorder.is_recording is True
        assert recorder.audio == mock_pa
        assert recorder.stream == mock_stream

    @patch('pyaudio.PyAudio')
    def test_start_recording_exception(self, mock_pyaudio, recorder):
        """Test recording start with exception."""
        mock_pyaudio.side_effect = Exception("PyAudio error")

        result = recorder.start_recording()

        assert result is False
        assert recorder.is_recording is False

    @patch('pyaudio.PyAudio')
    def test_stop_recording_success(self, mock_pyaudio, recorder):
        """Test successful recording stop."""
        # Mock PyAudio and stream
        mock_pa = MagicMock()
        mock_pyaudio.return_value = mock_pa

        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream

        # Set up recorder as if recording
        recorder.audio = mock_pa
        recorder.stream = mock_stream
        recorder.recorded_frames = [b'frame1', b'frame2']

        with patch('time.sleep'):
            result = recorder.stop_recording()

        assert result == b'frame1frame2'
        mock_stream.stop_stream.assert_called()
        mock_stream.close.assert_called()
        mock_pa.terminate.assert_called()

    def test_stop_recording_no_frames(self, recorder):
        """Test recording stop with no frames."""
        result = recorder.stop_recording()

        assert result is None


class TestAudioPlayer:
    """Test cases for AudioPlayer."""

    @pytest.fixture
    def player(self):
        """Create a test audio player."""
        return AudioPlayer()

    def test_init(self, player):
        """Test AudioPlayer initialization."""
        assert player.sample_rate == 16000
        assert player.channels == 1

    @patch('pyaudio.PyAudio')
    def test_play_audio_data_success(self, mock_pyaudio_class):
        """Test successful audio playback."""
        # Mock PyAudio instance before creating player
        mock_pa = MagicMock()
        mock_pyaudio_class.return_value = mock_pa

        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream

        # Create player instance after mocking
        player = AudioPlayer()

        # Create test PCM data (ensure it's valid 16-bit PCM)
        pcm_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'  # Valid 16-bit samples

        player.play_audio_data(pcm_data)

        # Verify stream was used
        mock_stream.write.assert_called()
        mock_stream.stop_stream.assert_called()
        mock_stream.close.assert_called()

    @patch('pyaudio.PyAudio')
    def test_play_audio_data_exception(self, mock_pyaudio, player):
        """Test audio playback with exception."""
        mock_pyaudio.side_effect = Exception("Playback error")

        pcm_data = generate_test_audio(duration_seconds=0.1)

        # Should not raise exception
        player.play_audio_data(pcm_data)


def test_generate_test_audio():
    """Test test audio generation."""
    duration = 0.5
    frequency = 440.0
    sample_rate = 16000

    audio_data = generate_test_audio(duration, frequency, sample_rate)

    assert isinstance(audio_data, bytes)
    assert len(audio_data) > 0

    # Verify the data is raw PCM (should be divisible by 2 for 16-bit samples)
    assert len(audio_data) % 2 == 0

    # Check that we have the expected number of samples
    expected_samples = int(duration * sample_rate)
    assert len(audio_data) == expected_samples * 2  # 2 bytes per 16-bit sample


@patch('pyaudio.PyAudio')
def test_play_audio_response(mock_pyaudio):
    """Test the play_audio_response function."""
    # Mock PyAudio
    mock_pa = MagicMock()
    mock_pyaudio.return_value = mock_pa

    mock_stream = MagicMock()
    mock_pa.open.return_value = mock_stream

    # Create test audio
    audio_data = generate_test_audio(duration_seconds=0.1)

    with patch('time.sleep'):
        play_audio_response(audio_data)

    # Verify PyAudio was used
    mock_pa.open.assert_called()


@patch('ug_game.core.voice.VoiceRecorder')
@patch('time.sleep')
def test_record_voice_input(mock_time_sleep, mock_voice_recorder_class):
    """Test the record_voice_input function."""
    mock_recorder = MagicMock()
    mock_voice_recorder_class.return_value = mock_recorder

    # Mock the recording process
    mock_recorder.start_recording.return_value = True
    mock_recorder.stop_recording.return_value = b'test_audio_data'

    with patch('builtins.print'):  # Suppress print statements
        result = record_voice_input(duration_seconds=2)

    assert result == b'test_audio_data'
    mock_recorder.start_recording.assert_called_once()
    mock_time_sleep.assert_called_once_with(2)
    mock_recorder.stop_recording.assert_called_once()


@patch('builtins.open', new_callable=mock_open)
def test_save_wav_file_debug_mode(mock_file):
    """Test saving WAV file in debug mode."""
    # Create valid PCM data (even number of bytes for 16-bit samples)
    audio_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'  # 4 samples

    with patch('pathlib.Path') as mock_path:
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)

        result = save_wav_file(audio_data, debug_mode=True)

    assert result is not None
    mock_file.assert_called()


@patch('builtins.open', new_callable=mock_open)
def test_save_wav_file_no_debug(mock_file):
    """Test saving WAV file without debug mode."""
    audio_data = b'test_wav_data'

    result = save_wav_file(audio_data, debug_mode=False)

    assert result is None
    mock_file.assert_not_called()


@patch('speech_recognition.Recognizer')
@patch('speech_recognition.AudioData')
def test_transcribe_audio_local_success(mock_audio_data_class, mock_recognizer_class):
    """Test successful local audio transcription."""
    # Mock recognizer and audio data
    mock_recognizer = MagicMock()
    mock_recognizer_class.return_value = mock_recognizer

    mock_audio_data = MagicMock()
    mock_audio_data_class.return_value = mock_audio_data

    mock_recognizer.recognize_google.return_value = "Hello world"

    # Create valid PCM data
    valid_pcm_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'

    result = transcribe_audio_local(valid_pcm_data)

    assert result == "Hello world"


@patch('speech_recognition.Recognizer')
def test_transcribe_audio_local_failure(mock_recognizer_class):
    """Test failed local audio transcription."""
    mock_recognizer = MagicMock()
    mock_recognizer_class.return_value = mock_recognizer

    mock_recognizer.recognize_google.side_effect = Exception("Recognition failed")

    result = transcribe_audio_local(b'test_audio_data')

    assert result is None


@pytest.fixture
def player():
    """Create a test audio player."""
    return AudioPlayer()


@pytest.mark.asyncio
async def test_play_audio_data_async(player):
    """Test asynchronous audio data playback."""
    audio_data = b"test_audio_data"

    with patch.object(player, 'play_audio_data') as mock_play:
        await player.play_audio_data_async(audio_data)

        mock_play.assert_called_once_with(audio_data)


@patch('pyaudio.PyAudio')
@pytest.mark.asyncio
async def test_play_audio_response_async(mock_pyaudio_class):
    """Test asynchronous audio response playback."""
    audio_data = b"test_audio_data"

    with patch('ug_game.core.voice.play_audio_response') as mock_play:
        await play_audio_response_async(audio_data, sample_rate=16000)

        mock_play.assert_called_once_with(audio_data, 16000)


@patch('speech_recognition.AudioData')
@patch('speech_recognition.Recognizer')
@pytest.mark.asyncio
async def test_transcribe_audio_local_async_success(mock_recognizer_class, mock_audio_data_class):
    """Test successful asynchronous local audio transcription."""
    mock_recognizer = MagicMock()
    mock_recognizer_class.return_value = mock_recognizer

    mock_audio_data = MagicMock()
    mock_audio_data_class.return_value = mock_audio_data

    mock_recognizer.recognize_google.return_value = "Hello world"

    # Create valid PCM data (same as sync test)
    valid_pcm_data = b'\x00\x01\x02\x03\x04\x05\x06\x07'

    result = await transcribe_audio_local_async(valid_pcm_data)

    assert result == "Hello world"


@patch('speech_recognition.Recognizer')
@pytest.mark.asyncio
async def test_transcribe_audio_local_async_failure(mock_recognizer_class):
    """Test failed asynchronous local audio transcription."""
    mock_recognizer = MagicMock()
    mock_recognizer_class.return_value = mock_recognizer
    mock_recognizer.recognize_google.side_effect = Exception("Recognition failed")

    result = await transcribe_audio_local_async(b"test_audio_data")

    assert result is None