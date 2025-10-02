import json
from pathlib import Path
from typing import List, Optional
from tix.models import Task

class ArchiveStorage:
    """JSON-based storage for archived tasks"""
    def __init__(self, storage_path: Path = None, context: str = None):
        self.context = context or self._get_active_context()
        if storage_path:
            self.storage_path = storage_path
        else:
            base_dir = Path.home() / ".tix"
            if self.context == "default":
                self.storage_path = base_dir / "archived.json"
            else:
                self.storage_path = base_dir / "contexts" / f"{self.context}_archived.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _get_active_context(self) -> str:
        try:
            active_context_path = Path.home() / ".tix" / "active_context"
            if active_context_path.exists():
                return active_context_path.read_text().strip()
        except:
            pass
        return "default"

    def _ensure_file(self):
        if not self.storage_path.exists():
            self._write_data({"tasks": []})

    def _read_data(self) -> dict:
        try:
            raw = json.loads(self.storage_path.read_text())
            if isinstance(raw, dict) and "tasks" in raw:
                return raw
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return {"tasks": []}

    def _write_data(self, data: dict):
        self.storage_path.write_text(json.dumps(data, indent=2))

    def load_tasks(self) -> List[Task]:
        data = self._read_data()
        return [Task.from_dict(item) for item in data["tasks"]]

    def save_tasks(self, tasks: List[Task]):
        data = {"tasks": [task.to_dict() for task in tasks]}
        self._write_data(data)

    def add_task(self, task: Task):
        tasks = self.load_tasks()
        tasks.append(task)
        self.save_tasks(tasks)

    def remove_task(self, task_id: int) -> Optional[Task]:
        tasks = self.load_tasks()
        for i, t in enumerate(tasks):
            if t.id == task_id:
                removed = tasks.pop(i)
                self.save_tasks(tasks)
                return removed
        return None

    def get_task(self, task_id: int) -> Optional[Task]:
        tasks = self.load_tasks()
        for t in tasks:
            if t.id == task_id:
                return t
        return None
