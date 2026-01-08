#!/usr/bin/env python3
"""Simple test script for audio recording."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ug_game.core.voice import record_voice_input

def main():
    print("Testing audio recording...")
    try:
        audio_data = record_voice_input(duration_seconds=2)
        if audio_data:
            print(f"Success! Recorded {len(audio_data)} bytes")
        else:
            print("Failed: No audio data")
    except KeyboardInterrupt:
        print("Interrupted")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()