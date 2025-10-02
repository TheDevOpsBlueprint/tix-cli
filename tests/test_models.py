import pytest
from tix.models import Task, Context
from datetime import datetime


def test_task_creation():
    """Test creating a task"""
    task = Task(id=1, text="Test task", priority="high")
    assert task.id == 1
    assert task.text == "Test task"
    assert task.priority == "high"
    assert task.completed == False
    assert task.tags == []
    assert task.is_global == False


def test_task_serialization():
    """Test task to_dict and from_dict"""
    task = Task(id=1, text="Test", priority="medium", tags=["work"], is_global=True)
    task_dict = task.to_dict()

    assert task_dict['id'] == 1
    assert task_dict['text'] == "Test"
    assert task_dict['tags'] == ["work"]
    assert task_dict['is_global'] == True

    # Test deserialization
    task2 = Task.from_dict(task_dict)
    assert task2.id == task.id
    assert task2.text == task.text
    assert task2.is_global == task.is_global


def test_task_backward_compatibility():
    """Test loading task without is_global field"""
    legacy_dict = {
        'id': 1,
        'text': "Legacy task",
        'priority': 'medium',
        'completed': False,
        'created_at': datetime.now().isoformat(),
        'completed_at': None,
        'tags': []
    }
    task = Task.from_dict(legacy_dict)
    assert task.is_global == False


def test_mark_done():
    """Test marking task as done"""
    task = Task(id=1, text="Test")
    assert task.completed == False
    assert task.completed_at is None

    task.mark_done()
    assert task.completed == True
    assert task.completed_at is not None


def test_context_creation():
    """Test creating a context"""
    context = Context(name="work", description="Work tasks")
    assert context.name == "work"
    assert context.description == "Work tasks"
    assert context.created_at is not None


def test_context_serialization():
    """Test context to_dict and from_dict"""
    context = Context(name="personal", description="Personal tasks")
    context_dict = context.to_dict()

    assert context_dict['name'] == "personal"
    assert context_dict['description'] == "Personal tasks"

    # Test deserialization
    context2 = Context.from_dict(context_dict)
    assert context2.name == context.name
    assert context2.description == context.description