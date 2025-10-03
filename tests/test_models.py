import pytest
from tix.models import Task
from datetime import datetime


def test_task_creation():
    """Test creating a task"""
    task = Task(id=1, text="Test task", priority="high")
    assert task.id == 1
    assert task.text == "Test task"
    assert task.priority == "high"
    assert task.completed == False
    assert task.tags == []


def test_task_serialization():
    """Test task to_dict and from_dict"""
    task = Task(id=1, text="Test", priority="medium", tags=["work"])
    task_dict = task.to_dict()

    assert task_dict['id'] == 1
    assert task_dict['text'] == "Test"
    assert task_dict['tags'] == ["work"]

    # Test deserialization
    task2 = Task.from_dict(task_dict)
    assert task2.id == task.id
    assert task2.text == task.text


def test_mark_done():
    """Test marking task as done"""
    task = Task(id=1, text="Test")
    assert task.completed == False
    assert task.completed_at is None

    task.mark_done()
    assert task.completed == True
    assert task.completed_at is not None