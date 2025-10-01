import json
from pathlib import Path
from typing import List, Optional
from tix.models import Task


class TaskStorage:
    """JSON-based storage for tasks (with indexing, pagination, and lazy loading)"""

    def __init__(self, storage_path: Path = None):
        """Initialize storage with default or custom path"""
        self.storage_path = storage_path or (Path.home() / ".tix" / "tasks.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

        # --- new: build in-memory index for fast lookups ---
        self._index: dict[int, Task] = {}
        self._next_id: int = 1
        self._load_index()

    def _ensure_file(self):
        """Ensure storage file exists"""
        if not self.storage_path.exists():
            self._write_data({"next_id": 1, "tasks": []})

    def _read_data(self) -> dict:
        """Read raw data from storage, ensuring backward compatibility"""
        try:
            raw = json.loads(self.storage_path.read_text())

            # --- backward compatibility ---
            if isinstance(raw, list):
                upgraded = []
                max_id = 0
                for i, t in enumerate(raw, start=1):
                    # skip invalid entries
                    if not isinstance(t, dict):
                        continue
                    # ensure valid ID
                    if "id" not in t or not isinstance(t["id"], int) or t["id"] <= 0:
                        t["id"] = i
                    max_id = max(max_id, t["id"])
                    upgraded.append(t)

                upgraded_data = {"next_id": max_id + 1, "tasks": upgraded}
                self._write_data(upgraded_data)
                return upgraded_data

            # new format (dict with tasks + next_id)
            if isinstance(raw, dict) and "tasks" in raw and "next_id" in raw:
                return raw

        except (json.JSONDecodeError, FileNotFoundError):
            pass

        # fallback if corrupt or missing
        return {"next_id": 1, "tasks": []}

    def _write_data(self, data: dict):
        """Write raw data to storage"""
        self.storage_path.write_text(json.dumps(data, indent=2))

    def _load_index(self):
        """Load tasks into memory and build index"""
        data = self._read_data()
        self._index = {t["id"]: Task.from_dict(t) for t in data["tasks"]}
        self._next_id = data["next_id"]

    def _save_index(self):
        """Persist index back to storage"""
        data = {
            "next_id": self._next_id,
            "tasks": [t.to_dict() for t in self._index.values()],
        }
        self._write_data(data)

    def load_tasks(self) -> List[Task]:
        """Load all tasks from storage"""
        return list(self._index.values())

    def save_tasks(self, tasks: List[Task]):
        """Save all tasks to storage"""
        self._index = {t.id: t for t in tasks}
        self._next_id = max((t.id for t in tasks), default=0) + 1
        self._save_index()

    def add_task(self, text: str, priority: str = 'medium', tags: List[str] = None) -> Task:
        """Add a new task and return it"""
        new_id = self._next_id
        new_task = Task(id=new_id, text=text, priority=priority, tags=tags or [])
        self._index[new_id] = new_task
        self._next_id += 1
        self._save_index()
        return new_task

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a specific task by ID"""
        return self._index.get(task_id)

    def update_task(self, task: Task):
        """Update an existing task"""
        if task.id in self._index:
            self._index[task.id] = task
            self._save_index()

    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID, return True if deleted"""
        if task_id in self._index:
            del self._index[task_id]
            self._save_index()
            return True
        return False

    def get_active_tasks(self) -> List[Task]:
        """Get all incomplete tasks"""
        return [t for t in self._index.values() if not t.completed]

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks"""
        return [t for t in self._index.values() if t.completed]


    def list_tasks(self, page: int = 1, page_size: int = 20) -> List[Task]:
        """Return a page of tasks (pagination for ls command)"""
        start = (page - 1) * page_size
        end = start + page_size
        return list(self._index.values())[start:end]

    def iter_tasks(self, start: int = 0, count: int = 20):
        """Yield tasks lazily (for large lists without loading all at once)"""
        for t in list(self._index.values())[start:start + count]:
            yield t
