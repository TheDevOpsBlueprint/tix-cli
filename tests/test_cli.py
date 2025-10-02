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
def test_report_markdown(runner):
    """Test markdown report generation"""
    with runner.isolated_filesystem():
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('[]')
        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)
        with patch('tix.cli.storage', test_storage):
            runner.invoke(cli, ['add', 'High priority task', '-p', 'high', '-t', 'work'])
            runner.invoke(cli, ['add', 'Medium task', '-p', 'medium'])
            runner.invoke(cli, ['done', '1'])
            result = runner.invoke(cli, ['report', '-f', 'markdown'])
            assert result.exit_code == 0
            assert '# TIX Task Report' in result.output
            assert '- [ ]' in result.output 
            assert '## Summary' in result.output

def test_list_empty(runner):
    """Test listing when no tasks"""
    with runner.isolated_filesystem():
        # Create empty storage file
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('{"next_id": 1, "tasks": []}')

        # Import and create storage instance
        from tix.storage.json_storage import TaskStorage
        from tix.models import Task
        test_storage = TaskStorage(temp_storage, context="test_isolated")
        
        # Override load_tasks to not load global tasks from default context
        def isolated_load_tasks():
            data = test_storage._read_data()
            return [Task.from_dict(item) for item in data["tasks"]]
        test_storage.load_tasks = isolated_load_tasks
        test_storage.get_active_tasks = lambda: [t for t in isolated_load_tasks() if not t.completed]

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


def test_add_empty_task_text(runner):
    """Empty task text should be rejected"""
    with runner.isolated_filesystem():
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('[]')

        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        with patch('tix.cli.storage', test_storage):
            result = runner.invoke(cli, ['add', ''])
            assert result.exit_code != 0
            assert 'cannot be empty' in result.output


def test_add_whitespace_only_task_text(runner):
    """Whitespace-only task text should be rejected"""
    with runner.isolated_filesystem():
        temp_storage = Path.cwd() / "tasks.json"
        temp_storage.write_text('[]')

        from tix.storage.json_storage import TaskStorage
        test_storage = TaskStorage(temp_storage)

        with patch('tix.cli.storage', test_storage):
            result = runner.invoke(cli, ['add', '   \t   '])
            assert result.exit_code != 0
            assert 'cannot be empty' in result.output


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
            

def test_add_task_with_attachments_and_links(runner, tmp_path):
    """Test adding a task with file attachments and URLs"""
    # Create a temporary file to attach
    temp_file = tmp_path / "example.txt"
    temp_file.write_text("Hello World")

    temp_storage = tmp_path / "tasks.json"
    temp_storage.write_text('[]')

    from tix.storage.json_storage import TaskStorage
    test_storage = TaskStorage(temp_storage)

    with patch('tix.cli.storage', test_storage):
        result = runner.invoke(cli, [
            'add', 'Task with attachments',
            '--attach', str(temp_file),
            '--link', 'https://example.com'
        ])
        assert result.exit_code == 0
        assert 'Added task' in result.output
        assert 'Attachments/Links added' in result.output

        # Verify task in storage
        task = test_storage.get_task(1)
        assert task is not None
        assert len(task.attachments) == 1
        assert task.links == ['https://example.com']


def test_edit_task_add_attachments_and_links(runner, tmp_path):
    """Test editing an existing task to add attachments and URLs"""
    temp_file = tmp_path / "edit.txt"
    temp_file.write_text("Edit content")

    temp_storage = tmp_path / "tasks.json"
    temp_storage.write_text(
        '[{"id": 1, "text": "Original task", "priority": "medium", "completed": false, "created_at": "2025-01-01T00:00:00", "completed_at": null, "tags": []}]'
    )

    from tix.storage.json_storage import TaskStorage
    test_storage = TaskStorage(temp_storage)

    with patch('tix.cli.storage', test_storage):
        result = runner.invoke(cli, [
            'edit', '1',
            '--attach', str(temp_file),
            '--link', 'https://edit.com'
        ])
        assert result.exit_code == 0
        assert 'attachments added' in result.output
        assert 'links added' in result.output

        task = test_storage.get_task(1)
        assert len(task.attachments) == 1
        assert task.links == ['https://edit.com']


def test_ls_shows_attachment_icon(runner, tmp_path):
    """Test that tasks with attachments/links show the 📎 icon"""
    temp_storage = tmp_path / "tasks.json"
    temp_storage.write_text(
        '[{"id": 1, "text": "Task with attachment", "priority": "medium", "completed": false, "created_at": "2025-01-01T00:00:00", "completed_at": null, "tags": [], "attachments": ["file.txt"], "links": ["https://example.com"]}]'
    )

    from tix.storage.json_storage import TaskStorage
    test_storage = TaskStorage(temp_storage)

    with patch('tix.cli.storage', test_storage):
        result = runner.invoke(cli, ['ls'])
        assert result.exit_code == 0
        assert '📎' in result.output


def test_open_command_opens_attachments_and_links(runner, tmp_path):
    """Test opening attachments and links without actually launching them"""
    temp_file = tmp_path / "open.txt"
    temp_file.write_text("Open me")

    temp_storage = tmp_path / "tasks.json"
    temp_storage.write_text(
        f'[{{"id": 1, "text": "Task to open", "priority": "medium", "completed": false, '
        f'"created_at": "2025-01-01T00:00:00", "completed_at": null, "tags": [], '
        f'"attachments": ["{temp_file}"], "links": ["https://example.com"]}}]'
    )

    from tix.storage.json_storage import TaskStorage
    test_storage = TaskStorage(temp_storage)

    with patch('tix.cli.storage', test_storage), \
         patch('subprocess.Popen') as mock_popen, \
         patch('os.startfile', create=True):

        result = runner.invoke(cli, ['open', '1'])
        assert result.exit_code == 0
        assert 'Opened file' in result.output
        assert 'Opened link' in result.output

        # Ensure the link was opened (regardless of platform details)
        calls = [str(call_args[0][0][1]) for call_args in mock_popen.call_args_list]
        assert "https://example.com" in calls
