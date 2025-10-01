import pytest
import tempfile
import json
from pathlib import Path
from tix.storage.json_storage import TaskStorage


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests"""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        storage_path = Path(f.name)
    storage = TaskStorage(storage_path)
    yield storage
    storage_path.unlink()  # Clean up


def test_add_task(temp_storage):
    """Test adding a task"""
    task = temp_storage.add_task("Test task", "high", ["work"])
    assert task.id == 1
    assert task.text == "Test task"
    assert task.priority == "high"
    assert "work" in task.tags

    task2 = temp_storage.add_task("Another task")
    assert task2.id == 2


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
    # Force reload after overwriting file manually
    temp_storage._load_index()

    tasks = temp_storage.load_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == 5
    assert tasks[0].text == "legacy"

    new_task = temp_storage.add_task("post-upgrade")
    assert new_task.id == 6

    data = json.loads(temp_storage.storage_path.read_text())
    assert isinstance(data, dict)
    assert "next_id" in data
    assert "tasks" in data



# --- new tests below ---

def test_pagination(temp_storage):
    """Test pagination with list_tasks"""
    for i in range(25):
        temp_storage.add_task(f"Task {i}")

    page1 = temp_storage.list_tasks(page=1, page_size=10)
    page2 = temp_storage.list_tasks(page=2, page_size=10)

    assert len(page1) == 10
    assert len(page2) == 10
    assert page1[0].text == "Task 0"
    assert page2[0].text == "Task 10"


def test_lazy_iteration(temp_storage):
    """Test lazy iteration with iter_tasks"""
    for i in range(5):
        temp_storage.add_task(f"Lazy {i}")

    tasks = list(temp_storage.iter_tasks(0, 3))
    assert len(tasks) == 3
    assert tasks[0].text.startswith("Lazy")


def test_active_and_completed(temp_storage):
    """Test filtering active and completed tasks"""
    t1 = temp_storage.add_task("Active task")
    t2 = temp_storage.add_task("Completed task")
    t2.mark_done()
    temp_storage.update_task(t2)

    active = temp_storage.get_active_tasks()
    completed = temp_storage.get_completed_tasks()

    assert any(t.text == "Active task" for t in active)
    assert any(t.text == "Completed task" for t in completed)
