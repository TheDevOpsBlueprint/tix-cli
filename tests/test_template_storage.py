import pytest
from tix.models import Task
from tix.storage.template_storage import TemplateStorage


@pytest.fixture
def temp_template_dir(tmp_path):
    """Fixture providing an isolated template storage directory"""
    storage = TemplateStorage(storage_dir=tmp_path)
    return storage


def test_save_and_load_template(temp_template_dir):
    """Test saving a template and then loading it"""
    task = Task(id=1, text="Template task", priority="high", tags=["urgent"], completed=False)
    task.links = ["https://example.com"]

    temp_template_dir.save_template(task, "my-template")
    
    path = temp_template_dir._template_path("my-template")
    assert path.exists(), "Template file should exist after saving"

    loaded = temp_template_dir.load_template("my-template")
    assert loaded["text"] == task.text
    assert loaded["priority"] == task.priority
    assert loaded["tags"] == list(task.tags)
    assert loaded["links"] == task.links


def test_load_missing_template(temp_template_dir):
    """Loading a non-existent template should return None"""
    assert temp_template_dir.load_template("missing") is None


def test_list_templates(temp_template_dir):
    """List all saved templates"""
    # Save multiple templates
    task = Task(id=1, text="Task1", priority="low", tags=[])
    temp_template_dir.save_template(task, "t1")
    temp_template_dir.save_template(task, "t2")
    
    templates = temp_template_dir.list_templates()
    assert "t1" in templates
    assert "t2" in templates
    assert len(templates) == 2

