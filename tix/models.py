from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass
class Task:
    """Task model with all necessary properties"""
    id: int
    text: str
    priority: str = 'medium'
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'text': self.text,
            'priority': self.priority,
            'completed': self.completed,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary"""
        return cls(**data)

    # --- NEW: SQLite support ---
    def to_row(self):
        """Convert Task to a SQLite row tuple (without id)"""
        return (
            self.text,
            self.priority,
            int(self.completed),  # store bool as 0/1
            self.created_at,
            self.completed_at,
            ",".join(self.tags),
        )

    @classmethod
    def from_row(cls, row):
        """Create Task from a SQLite row"""
        return cls(
            id=row["id"],
            text=row["text"],
            priority=row["priority"],
            completed=bool(row["completed"]),
            created_at=row["created_at"],
            completed_at=row["completed_at"],
            tags=row["tags"].split(",") if row["tags"] else []
        )

    def mark_done(self):
        """Mark task as completed with timestamp"""
        self.completed = True
        self.completed_at = datetime.now().isoformat()

    def add_tag(self, tag: str):
        """Add a tag to the task"""
        if tag not in self.tags:
            self.tags.append(tag)