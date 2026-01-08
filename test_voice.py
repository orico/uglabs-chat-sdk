#!/usr/bin/env python3
"""
Test script to verify voice recording works in interactive mode.
Run this with: python test_voice.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ug_game.core.voice import record_voice_input_async
import asyncio

async def test_voice_recording():
    print("🎤 Voice Recording Test")
    print("=" * 30)
    print("This test will record 3 seconds of audio.")
    print("Speak clearly into your microphone during recording.")
    print("Press Enter to start...")

    try:
        input("Press Enter to begin recording...")

        # Record audio
        audio_data = await record_voice_input_async(duration_seconds=3)

        if audio_data:
            print("✅ Recording completed!")
            print(f"📊 Audio data size: {len(audio_data)} bytes")

            # Analyze the audio
            import numpy as np
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            max_amp = np.max(np.abs(audio_array))

            print(f"RMS: {rms:.6f}")
            print(f"Max amplitude: {max_amp:.6f}")
            if rms > 100:
                print("🎉 Success! Audio input detected. Voice recording is working!")
            elif rms > 10:
                print("⚠️  Low audio level detected. Try speaking louder or closer to microphone.")
            else:
                print("❌ No audio detected. Check microphone permissions and connections.")

        else:
            print("❌ Recording failed - no audio data captured")

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    # Check if running interactively
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("❌ This test must be run in an interactive terminal.")
        print("   Run: python test_voice.py")
        sys.exit(1)

    asyncio.run(test_voice_recording())