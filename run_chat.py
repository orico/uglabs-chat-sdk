#!/usr/bin/env python3
"""Entry point for UG Game chat interface."""

import sys
from pathlib import Path

# Add src to path so we can import ug_game
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ug_game.cli.chat import main  # noqa: E402

if __name__ == "__main__":
    main()
