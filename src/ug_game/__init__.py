"""UG Game - Chat interface for UG Labs PUG API."""

__version__ = "0.1.0"

from .api.client import UGGameClient
from .core.config import settings

__all__ = ["UGGameClient", "settings"]