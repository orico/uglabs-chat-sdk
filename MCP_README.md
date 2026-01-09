# UG Game MCP Server

A Model Context Protocol (MCP) server that provides Claude Desktop with access to UG Game's text and voice chat capabilities.

## 🛠️ Features

- **Text Chat Tool**: Send text messages to the UG Game AI
- **Voice Chat Tool**: Record and transcribe voice messages for AI interaction
- **Real-time Communication**: WebSocket-based chat with the UG Labs PUG API
- **Audio Processing**: Full support for voice recording, playback, and audio format conversion

## 📋 Prerequisites

- Python 3.8+
- FFmpeg (for MP3 audio processing)
- Microphone access (for voice features)
- UG Labs API credentials (Developer API Key and Service Account API Key)
- Claude Desktop application

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
# Install the project dependencies
uv sync

# Or with pip
pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# UG Labs API Credentials (get from https://pug-playground.stg.uglabs.app/)
SERVICE_ACCOUNT_API_KEY=your-service-account-api-key-here
PLAYER_FEDERATED_ID=your-player-federated-id-here

# Optional: Create a new player if you don't have one
# DEVELOPER_API_KEY=your-developer-api-key-here
```

### 3. Test the MCP Server

Run the MCP server directly to verify it works:

```bash
python run_mcp.py
```

The server should initialize successfully and display connection status.

## 🔧 Claude Desktop Integration

### Method 1: Using the Configuration File

1. **Locate Claude Desktop's config directory:**
   - **macOS**: `~/Library/Application Support/Claude/`
   - **Windows**: `%APPDATA%/Claude/`
   - **Linux**: `~/.config/Claude/`

2. **Create or edit `claude_desktop_config.json`:**

   ```json
   {
     "mcpServers": {
       "ug-game": {
         "command": "python",
         "args": ["/full/path/to/your/ug-game/run_mcp.py"],
         "env": {
           "SERVICE_ACCOUNT_API_KEY": "your-service-account-api-key-here",
           "PLAYER_FEDERATED_ID": "your-player-federated-id-here"
         }
       }
     }
   }
   ```

   **Important**: Use the full absolute path to `run_mcp.py` in the `args` array.

3. **Restart Claude Desktop** to load the new configuration.

### Method 2: Copy Configuration File

Alternatively, you can copy the provided `claude_desktop_config.json` file to Claude's config directory:

```bash
# macOS
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/

# Windows (PowerShell)
Copy-Item claude_desktop_config.json "$env:APPDATA\Claude\"

# Linux
cp claude_desktop_config.json ~/.config/Claude/
```

Then edit the copied file to:
1. Replace the placeholder API keys with your actual credentials
2. Update the path in `args` to point to your `run_mcp.py` file

## 🎯 Using the Tools in Claude

Once configured, Claude will have access to two new tools:

### Text Chat Tool
Send text messages to the UG Game AI:

```
I want to send a text message to the AI
```

### Voice Chat Tool
Record voice input for AI interaction:

```
I want to record a 5-second voice message
```

Claude will automatically use the appropriate tool based on your request context.

## 🔍 Troubleshooting

### Common Issues

1. **"MCP server failed to start"**
   - Verify the path to `run_mcp.py` is correct in the config
   - Check that all dependencies are installed: `uv sync`
   - Ensure Python 3.8+ is being used

2. **"Authentication failed"**
   - Verify your API keys are correct
   - Check that your player account exists
   - Ensure you have the right permissions

3. **"Microphone access denied"**
   - Grant microphone permissions to Claude Desktop/Terminal
   - Test microphone access: `python -c "import sounddevice as sd; print(sd.query_devices())"`

4. **"Audio processing failed"**
   - Install FFmpeg: `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Ubuntu)
   - Verify audio device availability

### Debug Mode

Enable debug logging by setting the environment variable:

```json
{
  "mcpServers": {
    "ug-game": {
      "command": "python",
      "args": ["/path/to/run_mcp.py"],
      "env": {
        "SERVICE_ACCOUNT_API_KEY": "your-key",
        "PLAYER_FEDERATED_ID": "your-id",
        "DEBUG": "1"
      }
    }
  }
}
```

## 📁 Project Structure

```
ug-game/
├── src/mcp/
│   ├── __init__.py          # MCP package exports
│   ├── server.py            # Main MCP server implementation
│   ├── tools.py             # Tool definitions and handlers
│   └── config.py            # MCP-specific configuration
├── run_mcp.py               # MCP server entry point
├── claude_desktop_config.json  # Claude Desktop configuration template
└── MCP_README.md           # This file
```

## 🔒 Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive credentials
- The MCP server runs with the same permissions as Claude Desktop
- Voice recordings are processed locally before sending to the API

## 📞 Support

For issues with:
- **UG Game SDK**: Check the main README.md
- **MCP Protocol**: See [MCP documentation](https://modelcontextprotocol.io/)
- **Claude Desktop**: Check Claude's official documentation

## 🤝 Contributing

The MCP server is part of the UG Game SDK. Contributions follow the same guidelines as the main project.
