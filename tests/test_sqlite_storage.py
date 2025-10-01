import pytest
import tempfile
from pathlib import Path
from tix.storage.sqlite_storage import SQLiteTaskStorage

@pytest.fixture
def sqlite_storage():
    """Create temporary SQLite storage for tests"""
    db_path = Path(tempfile.mktemp(suffix=".db"))
    storage = SQLiteTaskStorage(db_path)
    yield storage
    db_path.unlink(missing_ok=True)

def test_add_and_get(sqlite_storage):
    task = sqlite_storage.add_task("SQLite test", "high", ["work"])
    retrieved = sqlite_storage.get_task(task.id)
    assert retrieved is not None
    assert retrieved.text == "SQLite test"
    assert retrieved.priority == "high"

def test_update(sqlite_storage):
    task = sqlite_storage.add_task("Old text")
    task.text = "Updated text"
    sqlite_storage.update_task(task)
    retrieved = sqlite_storage.get_task(task.id)
    assert retrieved.text == "Updated text"

def test_delete(sqlite_storage):
    task = sqlite_storage.add_task("To delete")
    deleted = sqlite_storage.delete_task(task.id)
    assert deleted
    assert sqlite_storage.get_task(task.id) is None

def test_active_and_completed(sqlite_storage):
    t1 = sqlite_storage.add_task("Active task")
    t2 = sqlite_storage.add_task("Done task")
    t2.mark_done()
    sqlite_storage.update_task(t2)

    active = sqlite_storage.get_active_tasks()
    completed = sqlite_storage.get_completed_tasks()

    assert any(t.text == "Active task" for t in active)
    assert any(t.text == "Done task" for t in completed)

def test_pagination_and_list(sqlite_storage):
    for i in range(25):
        sqlite_storage.add_task(f"Task {i}")

    page1 = sqlite_storage.list_tasks(page=1, page_size=10)
    page2 = sqlite_storage.list_tasks(page=2, page_size=10)

    assert len(page1) == 10
    assert page1[0].text == "Task 0"
    assert len(page2) == 10
    assert page2[0].text == "Task 10"
