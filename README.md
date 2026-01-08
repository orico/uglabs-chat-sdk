# UG Game - Chat Interface for UG Labs PUG API

A modern, production-ready chat interface for interacting with the UG Labs PUG API through text-based conversations.

## Features

- 🗣️ **Interactive Chat**: Real-time text conversations with AI
- 👤 **Player Management**: Create and manage player accounts
- ⌨️ **Command History**: Navigate through previous messages with arrow keys
- 🎨 **Rich Terminal UI**: Beautiful console interface with colors and formatting
- ⚙️ **Configuration Management**: Environment-based settings with validation
- 🏗️ **Production Structure**: Proper Python package layout

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
   pip install -r requirements.txt
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

## Project Structure

```
ug-game/
├── src/
│   └── ug_game/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py          # WebSocket API client
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── chat.py            # Chat interface
│       │   └── player.py          # Player management
│       └── core/
│           ├── __init__.py
│           └── config.py          # Configuration management
├── tests/                         # Test files
├── docs/                          # Documentation
├── scripts/                       # Utility scripts
├── pyproject.toml                 # Modern Python packaging
├── requirements.txt               # Dependencies
├── run_chat.py                    # Main entry point
└── README.md                      # This file
```

## Development

### Install in development mode

```bash
pip install -e .
```

This allows you to use the `ug-chat` and `ug-player` commands directly.

### Running Tests

```bash
pytest
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

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- [UG Labs Documentation](https://docs.uglabs.io/api/)
- [UG Labs Playground](https://pug-playground.stg.uglabs.app/)