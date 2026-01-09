"""Command-line tool for managing UG Game players."""

import asyncio
from typing import Any, Dict, List

import click
from rich.console import Console
from rich.table import Table

from ..api.client import UGGameAPIError, UGGameClient
from ..core.config import settings


async def list_players() -> List[Dict[str, Any]]:
    """List all players for the current team."""
    if not settings.developer_api_key:
        raise UGGameAPIError("DEVELOPER_API_KEY not set")

    client = UGGameClient()

    try:
        # Authenticate as developer
        await client.authenticate_player(
            settings.developer_api_key.get_secret_value(),
            "",  # Developer auth doesn't need federated_id
        )

        # This would need to be implemented in the client
        # For now, return empty list as placeholder
        return []
    finally:
        await client.disconnect()


async def create_player_cli(external_id: str) -> Dict[str, Any]:
    """Create a new player."""
    if not settings.developer_api_key:
        raise UGGameAPIError("DEVELOPER_API_KEY not set")

    client = UGGameClient()

    try:
        player_data = await client.create_player(
            settings.developer_api_key.get_secret_value(), external_id
        )
        return player_data
    finally:
        await client.disconnect()


@click.group()
def main():
    """UG Game Player Management CLI."""
    pass


@main.command()
@click.option("--external-id", required=True, help="External ID for the new player")
def create(external_id: str) -> None:
    """Create a new player."""
    console = Console()

    if not settings.developer_api_key:
        console.print("[red]Error: DEVELOPER_API_KEY not set[/red]")
        return

    try:
        player_data = asyncio.run(create_player_cli(external_id))
        console.print("[green]✓ Player created successfully![/green]")
        console.print(f"  Player PK: {player_data['pk']}")
        console.print(f"  External ID: {player_data['external_id']}")
        console.print(f"  Federated ID: {player_data['federated_id']}")
        console.print()
        console.print("[bold]Add this to your .env file:[/bold]")
        console.print(f"PLAYER_FEDERATED_ID={player_data['federated_id']}")

    except UGGameAPIError as e:
        console.print(f"[red]Error creating player: {e}[/red]")


@main.command()
def list():
    """List all players."""
    console = Console()

    if not settings.developer_api_key:
        console.print("[red]Error: DEVELOPER_API_KEY not set[/red]")
        return

    try:
        players = asyncio.run(list_players())

        table = Table(title="Players")
        table.add_column("PK", style="cyan")
        table.add_column("External ID", style="magenta")
        table.add_column("Federated ID", style="green")

        for player in players:
            table.add_row(
                str(player.get("pk", "")),
                player.get("external_id", ""),
                player.get("federated_id", ""),
            )

        console.print(table)

    except UGGameAPIError as e:
        console.print(f"[red]Error listing players: {e}[/red]")


if __name__ == "__main__":
    main()
