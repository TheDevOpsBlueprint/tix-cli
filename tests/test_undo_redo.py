import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner

from tix.storage.json_storage import TaskStorage
from tix.storage.history import HistoryManager
import tix.cli as cli


@pytest.fixture
def temp_env(monkeypatch):
    """Provide isolated storage + history for each test, patched into CLI"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "tasks.json"
        history_path = Path(tmpdir) / "history.json"

        storage = TaskStorage(
            storage_path=storage_path,
            context="isolated_test",
            history=HistoryManager(history_path=history_path),
        )
        history = storage.history

        # Patch CLI globals so undo/redo use our test files
        monkeypatch.setattr(cli, "storage", storage)
        monkeypatch.setattr(cli, "history", history)

        yield storage, history


@pytest.fixture
def runner():
    return CliRunner()


def test_undo_add_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Task to undo")
    assert storage.get_task(task.id) is not None

    result = runner.invoke(cli.undo)
    assert result.exit_code == 0
    assert storage.get_task(task.id) is None


def test_redo_add_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Redo task")
    runner.invoke(cli.undo)

    result = runner.invoke(cli.redo)
    assert result.exit_code == 0
    restored = storage.get_task(task.id)
    assert restored is not None
    assert restored.text == "Redo task"


def test_undo_delete_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Delete me")
    assert storage.get_task(task.id) is not None

    storage.delete_task(task.id)
    assert storage.get_task(task.id) is None

    result = runner.invoke(cli.undo)
    assert result.exit_code == 0
    assert storage.get_task(task.id) is not None
    assert storage.get_task(task.id).text == "Delete me"


def test_redo_delete_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Delete me again")
    storage.delete_task(task.id)
    runner.invoke(cli.undo)

    result = runner.invoke(cli.redo)
    assert result.exit_code == 0
    assert storage.get_task(task.id) is None


def test_undo_edit_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Original text")
    task.text = "Edited text"
    storage.update_task(task)

    assert storage.get_task(task.id).text == "Edited text"

    result = runner.invoke(cli.undo)
    assert result.exit_code == 0
    assert storage.get_task(task.id).text == "Original text"


def test_redo_edit_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Original text")
    task.text = "Edited text"
    storage.update_task(task)
    runner.invoke(cli.undo)

    result = runner.invoke(cli.redo)
    assert result.exit_code == 0
    assert storage.get_task(task.id).text == "Edited text"


def test_undo_done_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Finish me")
    task.completed = True
    storage.update_task(task)
    assert storage.get_task(task.id).completed

    result = runner.invoke(cli.undo)
    assert result.exit_code == 0
    assert not storage.get_task(task.id).completed


def test_redo_done_task(temp_env, runner):
    storage, _ = temp_env
    task = storage.add_task("Finish me again")
    task.completed = True
    storage.update_task(task)
    runner.invoke(cli.undo)

    result = runner.invoke(cli.redo)
    assert result.exit_code == 0
    assert storage.get_task(task.id).completed
