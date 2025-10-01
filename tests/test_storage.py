import pytest
import tempfile
import json
from pathlib import Path
from tix.storage.json_storage import TaskStorage
from unittest.mock import patch


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests with isolated context"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_tasks.json"
        # Create an isolated test context
        storage = TaskStorage(storage_path, context="isolated_test")
        
        # Override load_tasks to not load global tasks from default context during tests
        original_load_tasks = storage.load_tasks
        def isolated_load_tasks():
            data = storage._read_data()
            from tix.models import Task
            return [Task.from_dict(item) for item in data["tasks"]]
        
        storage.load_tasks = isolated_load_tasks
        yield storage


def test_add_task(temp_storage):
    """Test adding a task"""
    task = temp_storage.add_task("Test task", "high", ["work"])
    assert task.id == 1
    assert task.text == "Test task"
    assert task.priority == "high"
    assert "work" in task.tags
    assert task.is_global == False

    task2 = temp_storage.add_task("Another task")
    assert task2.id == 2


def test_add_global_task(temp_storage):
    """Test adding a global task"""
    task = temp_storage.add_task("Global task", "high", ["work"], is_global=True)
    assert task.id >= 1  # ID may vary depending on default context state
    assert task.text == "Global task"
    assert task.is_global == True


def test_get_task(temp_storage):
    """Test retrieving a task"""
    task = temp_storage.add_task("Test")
    retrieved = temp_storage.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id
    assert retrieved.text == "Test"


def test_delete_task(temp_storage):
    """Test deleting a task"""
    task = temp_storage.add_task("To delete")
    assert temp_storage.delete_task(task.id) is True
    assert temp_storage.get_task(task.id) is None

    new_task = temp_storage.add_task("New after delete")
    assert new_task.id > task.id


def test_update_task(temp_storage):
    """Test updating a task"""
    task = temp_storage.add_task("Original")
    task.text = "Updated"
    temp_storage.update_task(task)

    retrieved = temp_storage.get_task(task.id)
    assert retrieved is not None
    assert retrieved.text == "Updated"


def test_backward_compatibility(temp_storage):
    """Test reading old format (plain list) and upgrading"""
    old_data = [{"id": 5, "text": "legacy", "priority": "low", "tags": [], "completed": False}]
    temp_storage.storage_path.write_text(json.dumps(old_data))

    # Make sure we only load tasks from this storage, not from default context
    temp_storage.context = "isolated_test"
    tasks = temp_storage.load_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == 5
    assert tasks[0].text == "legacy"
    assert tasks[0].is_global == False  # Should default to False

    new_task = temp_storage.add_task("post-upgrade")
    assert new_task.id == 6

    data = json.loads(temp_storage.storage_path.read_text())
    assert isinstance(data, dict)
    assert "next_id" in data
    assert "tasks" in data

