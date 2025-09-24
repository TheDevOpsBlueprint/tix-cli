import pytest
from click.testing import CliRunner
from tix.cli import cli
import os
from unittest.mock import patch


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


def test_click_completion_environment_variable(runner):
    """Test that Click completion works with environment variable"""
    # Set the completion environment variable
    with patch.dict(os.environ, {'_TIX_COMPLETE': 'bash_complete'}):
        # This would normally trigger Click's completion mechanism
        # In test environment, we just verify it doesn't crash
        result = runner.invoke(cli, [])
        # Click handles completion internally when _TIX_COMPLETE is set
        # The exit code might not be 0 as Click exits early for completion
        assert result.exit_code in [0, 2]  # Accept either code


def test_basic_completion_support(runner):
    """Test that basic Click completion mechanism exists"""
    # Test that the CLI has the necessary attributes for completion
    assert hasattr(cli, 'name')
    assert cli.name is not None

    # Test that commands are properly registered
    commands = cli.list_commands(None)
    assert len(commands) > 0
    assert 'add' in commands
    assert 'ls' in commands
    assert 'done' in commands


def test_command_help_exists(runner):
    """Test that all commands have help text"""
    commands = ['add', 'ls', 'done', 'rm', 'clear', 'edit', 'filter', 'search', 'stats', 'report']

    for cmd in commands:
        result = runner.invoke(cli, [cmd, '--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output or 'Show this message' in result.output