# UG Game - SDK & Chat Interface for UG Labs PUG API

A comprehensive, production-ready SDK and chat interface for interacting with the UG Labs PUG API through text and voice conversations.

## Features

- 🗣️ **Interactive Chat**: Real-time text conversations with AI
- 🎤 **Voice Support**: Audio input/output with speech recognition and synthesis
- 👤 **Player Management**: Create and manage player accounts
- 📦 **Python SDK**: Full-featured SDK for programmatic access
- ⌨️ **Command History**: Navigate through previous messages with arrow keys
- 🎨 **Rich Terminal UI**: Beautiful console interface with colors and formatting
- ⚙️ **Configuration Management**: Environment-based settings with validation
- 🏗️ **Production Structure**: Proper Python package layout with 87 tests (46% coverage)
- 🔗 **Real API Integration**: Full integration tests with live API

## Installation

### Prerequisites

- Python 3.8+
- UG Labs API credentials

### Setup

1. **Clone or create the project structure**:
   ```bash
   # Project is already set up in ug-game/ directory
   cd ug-game
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Set up environment variables**:

   Create a `.env` file in the project root:

   ```bash
   # Required: Your developer API key (from https://pug-playground.stg.uglabs.app/profile)
   DEVELOPER_API_KEY=your-developer-api-key-here

   # Required: Your service account API key (from https://pug-playground.stg.uglabs.app/service-accounts)
   SERVICE_ACCOUNT_API_KEY=your-service-account-api-key-here

   # Optional: Specific player federated ID (can be created via /new command)
   PLAYER_FEDERATED_ID=your-player-federated-id-here
   ```

## Usage

### Start Chat Interface

```bash
python run_chat.py
```

Or use the installed command (after `pip install -e .`):

```bash
ug-chat
```

### Available Commands

- `/new <external_id>` - Create a new player account
- `/quit` or `/exit` - Exit the chat
- `↑/↓` arrow keys - Navigate through message history

### Player Management

```bash
# Create a new player
python -m ug_game.cli.player create --external-id "user@example.com"

# List all players
python -m ug_game.cli.player list
```

### Using the SDK

```python
from ug_game.sdk.session import ChatSession
from ug_game.sdk.types import ChatCallbacks, ChatConfig

# Set up callbacks
callbacks = ChatCallbacks(
    on_text_response=lambda text: print(f"AI: {text}"),
    on_audio_response=lambda audio: print(f"Received audio: {len(audio)} bytes"),
    on_error=lambda error: print(f"Error: {error}")
)

# Create session
config = ChatConfig(debug_mode=True)
session = ChatSession(callbacks=callbacks, config=config)

# Initialize and chat
await session.initialize(
    service_account_key="your-service-key",
    player_federated_id="your-player-id",
    system_prompt="You are a helpful assistant."
)

response = await session.send_text("Hello!")
print(f"Response: {response.text}")

await session.disconnect()
```

## Project Structure

```
ug-game/
├── src/
│   └── ug_game/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py          # WebSocket API client (92% test coverage)
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── chat.py            # Chat interface (0% coverage)
│       │   └── player.py          # Player management (98% coverage)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py          # Configuration management (100% coverage)
│       │   └── voice.py           # Voice processing (72% coverage)
│       └── sdk/
│           ├── __init__.py
│           ├── session.py         # SDK session management (70% coverage)
│           └── types.py           # SDK types and callbacks (73% coverage)
├── tests/                         # Comprehensive test suite (87 tests)
│   ├── conftest.py                # Test configuration and fixtures
│   ├── test_*.py                  # Unit and integration tests
├── scripts/                       # Utility scripts
├── pyproject.toml                 # Modern Python packaging with uv
├── uv.lock                        # Dependency lock file
├── run_chat.py                    # Main entry point
└── README.md                      # This file
```

## Development

### Install in development mode

```bash
uv sync --extra dev
```

This allows you to use the `ug-chat` and `ug-player` commands directly.

### Running Tests

```bash
# Run all tests (87 tests, 46% coverage)
pytest

# Run with coverage report
pytest --cov=ug_game --cov-report=html

# Run integration tests (requires .env credentials)
pytest tests/test_sdk_integration.py -v

# Run specific test categories
pytest tests/test_client.py    # API client tests (92% coverage)
pytest tests/test_voice.py     # Voice processing tests
pytest tests/test_sdk_session.py  # SDK tests
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/
```

## API Documentation

- [UG Labs API Documentation](https://docs.uglabs.io/api/)
- [Live API Explorer](https://pug.stg.uglabs.app/docs#/)

## Configuration

The application uses the following configuration (all configurable via environment variables):

- `DEVELOPER_API_KEY`: API key for developer operations (creating players)
- `SERVICE_ACCOUNT_API_KEY`: API key for player authentication
- `PLAYER_FEDERATED_ID`: Specific player to chat as
- `API_BASE_URL`: Base URL for REST API (default: https://pug.stg.uglabs.app)
- `WEBSOCKET_URL`: WebSocket URL for chat (default: wss://pug.stg.uglabs.app/interact)
- `DEFAULT_PROMPT`: Default AI prompt for conversations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

Cant be used commercially

## Support

For support and questions:
- [UG Labs Documentation](https://docs.uglabs.io/api/)
- [UG Labs Playground](https://pug-playground.stg.uglabs.app/)
