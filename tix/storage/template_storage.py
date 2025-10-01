import json
from pathlib import Path
from typing import List, Optional
from tix.models import Task


class TemplateStorage:
    """JSON-based storage for task templates"""

    def __init__(self, storage_dir: Path = None):
        """Initialize template storage with default or custom path"""
        self.storage_dir = storage_dir or (Path.home() / ".tix" / "templates")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _template_path(self, name: str) -> Path:
        """Return the full path for a template"""
        return self.storage_dir / f"{name}.json"

    def save_template(self, task: Task, name: str):
        """Save only the relevant template fields (no id / timestamps)."""
        path = self._template_path(name)
        data = {
            "text": task.text,
            "priority": task.priority,
            "tags": list(task.tags) if task.tags else [],
            "links": getattr(task, "links", []) or [],
        }
        path.write_text(json.dumps(data, indent=2))

    def load_template(self, name: str) -> Optional[Task]:
        """Load a template by name"""
        path = self._template_path(name)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def list_templates(self) -> List[str]:
        """List all template names"""
        return [p.stem for p in sorted(self.storage_dir.glob("*.json"))]

    def delete_template(self, name: str) -> bool:
        """Delete a template by name"""
        path = self._template_path(name)
        if path.exists():
            path.unlink()
            return True
        return False
