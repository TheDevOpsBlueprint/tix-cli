import pytest
from click.testing import CliRunner
from tix.cli import cli
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


@pytest.fixture
def runner():
    """Create a CLI runner for testing"""
    return CliRunner()


def test_cli_version(runner):
    """Test version command"""
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'version 0.8.0' in result.output  # Fixed: Changed from 0.1.0 to 0.8.0


def test_add_task(runner):
    """Test adding a task via CLI"""
    with runner.isolated_filesystem():
        # Create a temporary storage file
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('[]')

        # Import and create storage instance
        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        # Patch the module-level storage object
        with patch('tix.cli.storage', test_storage):
            result = runner.invoke(cli, ['add', 'Test task'])
            assert result.exit_code == 0
            assert 'Added task' in result.output
            assert 'Test task' in result.output


def test_list_empty(runner):
    """Test listing when no tasks"""
    with runner.isolated_filesystem():
        # Create empty storage file
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('[]')

        # Import and create storage instance
        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        # Patch the module-level storage object directly
        with patch('tix.cli.storage', test_storage):
            result = runner.invoke(cli, ['ls'])
            assert result.exit_code == 0
            assert 'No tasks found' in result.output


def test_help(runner):
    """Test help command"""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'TIX - Lightning-fast terminal task manager' in result.output


def test_add_and_list(runner):
    """Test adding a task and then listing it"""
    with runner.isolated_filesystem():
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('[]')

        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        with patch('tix.cli.storage', test_storage):
            # Add a task
            result = runner.invoke(cli, ['add', 'My task', '-p', 'high'])
            assert result.exit_code == 0
            assert 'Added task' in result.output

            # List tasks
            result = runner.invoke(cli, ['ls'])
            assert result.exit_code == 0
            # Should show the task in the output
            assert 'My task' in result.output or 'high' in result.output


def test_done_command(runner):
    """Test marking a task as done"""
    with runner.isolated_filesystem():
        temp_storage = Path.cwd() / "tasks.json"
        # Pre-populate with a task
        temp_storage.write_text(
            '[{"id": 1, "text": "Test task", "priority": "medium", "completed": false, "created_at": "2025-01-01T00:00:00", "completed_at": null, "tags": []}]')

        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        with patch('tix.cli.storage', test_storage):
            result = runner.invoke(cli, ['done', '1'])
            assert result.exit_code == 0
            assert 'Completed' in result.output


def test_filter_command(runner):
    """Test filtering tasks with different options including short flags"""
    with runner.isolated_filesystem():
        temp_storage = Path.cwd() / "tasks.json"
        # Pre-populate with tasks: one completed task with high priority and work tag,
        # one active task with medium priority and urgent tag
        temp_storage.write_text(
            '[{"id": 1, "text": "Completed task", "priority": "high", "completed": true, '
            '"created_at": "2025-01-01T00:00:00", "completed_at": "2025-01-02T00:00:00", "tags": ["work"]}, '
            '{"id": 2, "text": "Active task", "priority": "medium", "completed": false, '
            '"created_at": "2025-01-01T00:00:00", "completed_at": null, "tags": ["urgent"]}]')

        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        with patch('tix.cli.storage', test_storage):
            # Test filter by priority
            result = runner.invoke(cli, ['filter', '-p', 'high'])
            assert result.exit_code == 0
            assert 'Completed task' in result.output
            assert 'Active task' not in result.output

            # Test filter by tag
            result = runner.invoke(cli, ['filter', '-t', 'urgent'])
            assert result.exit_code == 0
            assert 'Active task' in result.output
            assert 'Completed task' not in result.output

            # Test filter by completed status using long option
            result = runner.invoke(cli, ['filter', '--completed'])
            assert result.exit_code == 0
            assert 'Completed task' in result.output
            assert 'Active task' not in result.output

            # Test filter by active status using long option
            result = runner.invoke(cli, ['filter', '--active'])
            assert result.exit_code == 0
            assert 'Active task' in result.output
            assert 'Completed task' not in result.output

            # Test filter by completed status using new short option
            result = runner.invoke(cli, ['filter', '-c'])
            assert result.exit_code == 0
            assert 'Completed task' in result.output
            assert 'Active task' not in result.output

            # Test filter by active status using new short option
            result = runner.invoke(cli, ['filter', '-a'])
            assert result.exit_code == 0
            assert 'Active task' in result.output
            assert 'Completed task' not in result.output