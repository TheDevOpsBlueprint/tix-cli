import sqlite3
from pathlib import Path
from typing import List, Optional
from tix.models import Task

class SQLiteTaskStorage:
    """SQLite-based storage for tasks"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (Path.home() / ".tix" / "tasks.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                priority TEXT,
                completed INTEGER DEFAULT 0,
                created_at TEXT,
                completed_at TEXT,
                tags TEXT
            )
        """)
        self.conn.commit()

    def add_task(self, text: str, priority: str = "medium", tags: List[str] = None) -> Task:
        task = Task(id=0, text=text, priority=priority, tags=tags or [])
        cur = self.conn.execute(
            "INSERT INTO tasks (text, priority, completed, created_at, completed_at, tags) VALUES (?, ?, ?, ?, ?, ?)",
            task.to_row()
        )
        self.conn.commit()
        task.id = cur.lastrowid
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        cur = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        row = cur.fetchone()
        return Task.from_row(row) if row else None

    def load_tasks(self) -> List[Task]:
        cur = self.conn.execute("SELECT * FROM tasks ORDER BY id")
        return [Task.from_row(row) for row in cur.fetchall()]

    def update_task(self, task: Task):
        self.conn.execute(
            "UPDATE tasks SET text=?, priority=?, completed=?, created_at=?, completed_at=?, tags=? WHERE id=?",
            (*task.to_row(), task.id)
        )
        self.conn.commit()

    def delete_task(self, task_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def get_active_tasks(self) -> List[Task]:
        cur = self.conn.execute("SELECT * FROM tasks WHERE completed=0 ORDER BY id")
        return [Task.from_row(row) for row in cur.fetchall()]

    def get_completed_tasks(self) -> List[Task]:
        cur = self.conn.execute("SELECT * FROM tasks WHERE completed=1 ORDER BY id")
        return [Task.from_row(row) for row in cur.fetchall()]

    def list_tasks(self, page: int = 1, page_size: int = 20) -> List[Task]:
        offset = (page - 1) * page_size
        cur = self.conn.execute("SELECT * FROM tasks ORDER BY id LIMIT ? OFFSET ?", (page_size, offset))
        return [Task.from_row(row) for row in cur.fetchall()]

    def iter_tasks(self, start: int = 0, count: int = 20):
        cur = self.conn.execute("SELECT * FROM tasks ORDER BY id LIMIT ? OFFSET ?", (count, start))
        for row in cur.fetchall():
            yield Task.from_row(row)
