from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

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
    
    # Time tracking fields
    estimate: Optional[int] = None
    time_spent: int = 0
    started_at: Optional[str] = None
    time_logs: List[Dict] = field(default_factory=list)

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
            'estimate': self.estimate,
            'time_spent': self.time_spent,
            'started_at': self.started_at,
            'time_logs': self.time_logs
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary (handles old tasks safely)"""
        return cls(
            id=data['id'],
            text=data['text'],
            priority=data.get('priority', 'medium'),
            completed=data.get('completed', False),
            created_at=data.get('created_at', datetime.now().isoformat()),
            completed_at=data.get('completed_at'),
            tags=data.get('tags', []),
            attachments=data.get('attachments', []),
            links=data.get('links', []),
            estimate=data.get('estimate'),
            time_spent=data.get('time_spent', 0),
            started_at=data.get('started_at'),
            time_logs=data.get('time_logs', [])
        )

    def mark_done(self):
        """Mark task as completed with timestamp"""
        self.completed = True
        self.completed_at = datetime.now().isoformat()

    def add_tag(self, tag: str):
        """Add a tag to the task"""
        if tag not in self.tags:
            self.tags.append(tag)

    def start_timer(self):
        """Start tracking time for this task"""
        if self.started_at:
            raise ValueError("Timer already running for this task")
        self.started_at = datetime.now().isoformat()

    def stop_timer(self):
        """Stop tracking time and log the duration"""
        if not self.started_at:
            raise ValueError("Timer not running for this task")
        
        start_time = datetime.fromisoformat(self.started_at)
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds() / 60)
        
        self.time_logs.append({
            'started_at': self.started_at,
            'ended_at': end_time.isoformat(),
            'duration': duration
        })
        
        self.time_spent += duration
        self.started_at = None
        
        return duration

    def is_timer_running(self) -> bool:
        """Check if timer is currently running"""
        return self.started_at is not None

    def get_current_session_duration(self) -> int:
        """Get duration of current timer session in minutes"""
        if not self.started_at:
            return 0
        start_time = datetime.fromisoformat(self.started_at)
        duration = int((datetime.now() - start_time).total_seconds() / 60)
        return duration

    def format_time(self, minutes: int) -> str:
        """Format minutes into human readable format"""
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h {mins}m"

    def get_time_remaining(self) -> Optional[int]:
        """Get remaining time based on estimate"""
        if not self.estimate:
            return None
        return self.estimate - self.time_spent