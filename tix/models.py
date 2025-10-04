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
    attachments: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    is_global: bool = False  # New field for global tasks
    parent_id: Optional[int] = None  # ID of parent task (for subtasks)
    subtasks: List[int] = field(default_factory=list)  # List of subtask IDs
    notes: str = ""  # Additional notes/checklist for the task

    def to_dict(self) -> dict:
        """Convert task to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'text': self.text,
            'priority': self.priority,
            'completed': self.completed,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'tags': self.tags,
            'attachments': self.attachments,
            'links': self.links,
            'is_global': self.is_global,
            'parent_id': self.parent_id,
            'subtasks': self.subtasks,
            'notes': self.notes
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary (handles old tasks safely)"""
        # Handle legacy tasks without new fields
        if 'attachments' not in data:
            data['attachments'] = []
        if 'links' not in data:
            data['links'] = []
        if 'is_global' not in data:
            data['is_global'] = False
        if 'parent_id' not in data:
            data['parent_id'] = None
        if 'subtasks' not in data:
            data['subtasks'] = []
        if 'notes' not in data:
            data['notes'] = ""
        return cls(**data)

    def mark_done(self):
        """Mark task as completed with timestamp"""
        self.completed = True
        self.completed_at = datetime.now().isoformat()

    def add_tag(self, tag: str):
        """Add a tag to the task"""
        if tag not in self.tags:
            self.tags.append(tag)

    def add_subtask(self, subtask_id: int):
        """Add a subtask ID to this task"""
        if subtask_id not in self.subtasks:
            self.subtasks.append(subtask_id)

    def remove_subtask(self, subtask_id: int):
        """Remove a subtask ID from this task"""
        if subtask_id in self.subtasks:
            self.subtasks.remove(subtask_id)

    def get_subtask_count(self) -> int:
        """Get the number of subtasks"""
        return len(self.subtasks)

    def is_parent_task(self) -> bool:
        """Check if this task has subtasks"""
        return len(self.subtasks) > 0

    def is_subtask(self) -> bool:
        """Check if this task is a subtask"""
        return self.parent_id is not None

    def get_depth_level(self) -> int:
        """Get the depth level of this task (0 = root, 1 = subtask, 2 = sub-subtask)"""
        if self.parent_id is None:
            return 0
        return 1  # For now, we'll implement 2-level nesting later


@dataclass
class Context:
    """Context model for managing separate workspaces"""
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert context to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'created_at': self.created_at,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create context from dictionary"""
        return cls(**data)