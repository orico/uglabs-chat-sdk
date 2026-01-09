"""Tests for UG Game player CLI commands."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from pydantic import SecretStr

from ug_game.api.client import UGGameAPIError
from ug_game.cli.player import create_player_cli, list_players, main
from ug_game.core.config import settings


class TestPlayerFunctions:
    """Test cases for player CLI functions."""

    @pytest.mark.asyncio
    async def test_list_players_success(self):
        """Test successful player listing."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.UGGameClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock successful authentication and empty player list
                mock_client.authenticate_player.return_value = None

                result = await list_players()

                assert result == []
                mock_client.authenticate_player.assert_called_once_with('test_key', '')
                mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_players_no_api_key(self):
        """Test player listing without API key."""
        with patch.object(settings, 'developer_api_key', None):
            with pytest.raises(UGGameAPIError, match="DEVELOPER_API_KEY not set"):
                await list_players()

    @pytest.mark.asyncio
    async def test_create_player_cli_success(self):
        """Test successful player creation."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.UGGameClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                expected_player_data = {
                    'pk': 123,
                    'external_id': 'test_external',
                    'federated_id': 'test_federated'
                }

                mock_client.create_player.return_value = expected_player_data

                result = await create_player_cli('test_external')

                assert result == expected_player_data
                mock_client.create_player.assert_called_once_with('test_key', 'test_external')
                mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_player_cli_no_api_key(self):
        """Test player creation without API key."""
        with patch.object(settings, 'developer_api_key', None):
            with pytest.raises(UGGameAPIError, match="DEVELOPER_API_KEY not set"):
                await create_player_cli('test_external')


class TestPlayerCLICommands:
    """Test cases for player CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_create_command_success(self, runner):
        """Test successful player creation command."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.create_player_cli') as mock_create:
                mock_create.return_value = {
                    'pk': 123,
                    'external_id': 'test_external',
                    'federated_id': 'test_federated'
                }

                result = runner.invoke(main, ['create', '--external-id', 'test_external'])

                assert result.exit_code == 0
                assert '✓ Player created successfully!' in result.output
                assert 'Player PK: 123' in result.output
                assert 'External ID: test_external' in result.output
                assert 'Federated ID: test_federated' in result.output
                assert 'PLAYER_FEDERATED_ID=test_federated' in result.output

    def test_create_command_no_api_key(self, runner):
        """Test player creation command without API key."""
        with patch.object(settings, 'developer_api_key', None):
            result = runner.invoke(main, ['create', '--external-id', 'test_external'])

            assert result.exit_code == 0
            assert 'Error: DEVELOPER_API_KEY not set' in result.output

    def test_create_command_api_error(self, runner):
        """Test player creation command with API error."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.create_player_cli') as mock_create:
                mock_create.side_effect = UGGameAPIError("API error")

                result = runner.invoke(main, ['create', '--external-id', 'test_external'])

                assert result.exit_code == 0
                assert 'Error creating player: API error' in result.output

    def test_list_command_success(self, runner):
        """Test successful player listing command."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.list_players') as mock_list:
                mock_list.return_value = [
                    {'pk': 1, 'external_id': 'ext1', 'federated_id': 'fed1'},
                    {'pk': 2, 'external_id': 'ext2', 'federated_id': 'fed2'}
                ]

                result = runner.invoke(main, ['list'])

                assert result.exit_code == 0
                assert 'Players' in result.output
                assert 'ext1' in result.output
                assert 'fed1' in result.output
                assert 'ext2' in result.output
                assert 'fed2' in result.output

    def test_list_command_empty_list(self, runner):
        """Test player listing command with empty list."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.list_players') as mock_list:
                mock_list.return_value = []

                result = runner.invoke(main, ['list'])

                assert result.exit_code == 0
                assert 'Players' in result.output

    def test_list_command_no_api_key(self, runner):
        """Test player listing command without API key."""
        with patch.object(settings, 'developer_api_key', None):
            result = runner.invoke(main, ['list'])

            assert result.exit_code == 0
            assert 'Error: DEVELOPER_API_KEY not set' in result.output

    def test_list_command_api_error(self, runner):
        """Test player listing command with API error."""
        with patch.object(settings, 'developer_api_key', SecretStr('test_key')):
            with patch('ug_game.cli.player.list_players') as mock_list:
                mock_list.side_effect = UGGameAPIError("API error")

                result = runner.invoke(main, ['list'])

                assert result.exit_code == 0
                assert 'Error listing players: API error' in result.output

    def test_main_command_help(self, runner):
        """Test main command help."""
        result = runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        assert 'UG Game Player Management CLI' in result.output
        assert 'create' in result.output
        assert 'list' in result.output

    def test_create_command_help(self, runner):
        """Test create command help."""
        result = runner.invoke(main, ['create', '--help'])

        assert result.exit_code == 0
        assert 'Create a new player' in result.output
        assert '--external-id' in result.output

    def test_list_command_help(self, runner):
        """Test list command help."""
        result = runner.invoke(main, ['list', '--help'])

        assert result.exit_code == 0
        assert 'List all players' in result.output