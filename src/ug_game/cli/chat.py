"""Command-line chat interface for UG Game."""

import asyncio
from typing import List, Optional

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ..api.client import UGGameClient, UGGameAPIError
from ..core.config import settings


class ChatSession:
    """Manages chat session state and history."""

    def __init__(self):
        self.client = UGGameClient()
        self.console = Console()
        self.message_history: List[str] = []
        self.history_index = -1
        self.is_connected = False

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
            self.console.print("[bold green]Chat ready! Type your message or use commands:[/bold green]")
            self.console.print("[dim]/new - Create new player[/dim]")
            self.console.print("[dim]/quit - Exit chat[/dim]")
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

    async def send_message(self, text: str) -> None:
        """Send a message and display the response."""
        if not self.is_connected:
            self.console.print("[red]Not connected. Please restart the chat.[/red]")
            return

        try:
            self.console.print(f"[bold blue]You:[/bold blue] {text}")

            # Send message and collect responses
            responses = []
            async for response in self.client.send_text_interaction(text, audio_output=False):
                if response.get("event") == "text":
                    responses.append(response.get("text", ""))

            # Display AI response
            if responses:
                full_response = "".join(responses)
                self.console.print(f"[bold green]AI:[/bold green] {full_response}")
                self.message_history.append(text)
            else:
                self.console.print("[yellow]No response received[/yellow]")

        except UGGameAPIError as e:
            self.console.print(f"[red]Error sending message: {e}[/red]")

    async def cleanup(self) -> None:
        """Clean up the chat session."""
        if self.client:
            await self.client.disconnect()
        self.is_connected = False


def create_key_bindings() -> KeyBindings:
    """Create custom key bindings for the chat prompt."""
    bindings = KeyBindings()

    @bindings.add('up')
    def _(event):
        """Navigate up in history."""
        # This will be handled by prompt_toolkit's history
        pass

    @bindings.add('down')
    def _(event):
        """Navigate down in history."""
        # This will be handled by prompt_toolkit's history
        pass

    return bindings


async def chat_loop(session: ChatSession) -> None:
    """Main chat loop."""
    history = InMemoryHistory()
    prompt_session = PromptSession(history=history, key_bindings=create_key_bindings())

    try:
        await session.initialize()

        while True:
            try:
                # Get user input with history support
                user_input = await prompt_session.prompt_async("You> ")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    command = user_input[1:].strip().lower()

                    if command == "quit" or command == "exit":
                        break
                    elif command.startswith("new"):
                        # Parse external_id from command
                        parts = command.split(" ", 1)
                        if len(parts) < 2:
                            session.console.print("[red]Usage: /new <external_id>[/red]")
                            continue

                        external_id = parts[1].strip()
                        try:
                            federated_id = await session.create_new_player(external_id)
                            session.console.print(f"[green]New player federated_id: {federated_id}[/green]")
                        except UGGameAPIError:
                            pass
                        continue
                    else:
                        session.console.print(f"[red]Unknown command: {command}[/red]")
                        continue

                # Send regular message
                await session.send_message(user_input)

            except KeyboardInterrupt:
                break
            except EOFError:
                break

    finally:
        await session.cleanup()


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