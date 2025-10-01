import pytest
import tempfile
import json
from pathlib import Path
from tix.storage.context_storage import ContextStorage


@pytest.fixture
def temp_context_storage():
    """Create temporary context storage for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "contexts.json"
        active_context_path = Path(tmpdir) / "active_context"
        storage = ContextStorage(storage_path)
        storage.active_context_path = active_context_path
        yield storage


def test_default_context_creation(temp_context_storage):
    """Test that default context is created automatically"""
    contexts = temp_context_storage.load_contexts()
    assert len(contexts) >= 1
    assert any(c.name == "default" for c in contexts)
    assert temp_context_storage.get_active_context() == "default"


def test_add_context(temp_context_storage):
    """Test adding a new context"""
    context = temp_context_storage.add_context("work", "Work tasks")
    assert context.name == "work"
    assert context.description == "Work tasks"
    
    # Verify it was saved
    retrieved = temp_context_storage.get_context("work")
    assert retrieved is not None
    assert retrieved.name == "work"


def test_add_duplicate_context(temp_context_storage):
    """Test that adding duplicate context raises error"""
    temp_context_storage.add_context("work")
    
    with pytest.raises(ValueError, match="already exists"):
        temp_context_storage.add_context("work")


def test_switch_context(temp_context_storage):
    """Test switching active context"""
    temp_context_storage.add_context("personal")
    temp_context_storage.set_active_context("personal")
    
    assert temp_context_storage.get_active_context() == "personal"


def test_switch_to_nonexistent_context(temp_context_storage):
    """Test that switching to nonexistent context raises error"""
    with pytest.raises(ValueError, match="does not exist"):
        temp_context_storage.set_active_context("nonexistent")


def test_delete_context(temp_context_storage):
    """Test deleting a context"""
    temp_context_storage.add_context("temp")
    assert temp_context_storage.delete_context("temp") is True
    assert temp_context_storage.get_context("temp") is None


def test_cannot_delete_default_context(temp_context_storage):
    """Test that default context cannot be deleted"""
    with pytest.raises(ValueError, match="Cannot delete the default context"):
        temp_context_storage.delete_context("default")


def test_delete_active_context_switches_to_default(temp_context_storage):
    """Test that deleting active context switches to default"""
    temp_context_storage.add_context("temp")
    temp_context_storage.set_active_context("temp")
    
    temp_context_storage.delete_context("temp")
    assert temp_context_storage.get_active_context() == "default"


def test_list_contexts(temp_context_storage):
    """Test listing all contexts"""
    temp_context_storage.add_context("work")
    temp_context_storage.add_context("personal")
    
    contexts = temp_context_storage.load_contexts()
    names = [c.name for c in contexts]
    
    assert "default" in names
    assert "work" in names
    assert "personal" in names
    assert len(contexts) >= 3


def test_context_exists(temp_context_storage):
    """Test checking if context exists"""
    assert temp_context_storage.context_exists("default") is True
    assert temp_context_storage.context_exists("nonexistent") is False
    
    temp_context_storage.add_context("work")
    assert temp_context_storage.context_exists("work") is True
