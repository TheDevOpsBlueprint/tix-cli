from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict

STATUS_CHOICES = ['todo', 'in_progress', 'review', 'blocked', 'done']


@dataclass
class Task:
    """Task model with all necessary properties for team collaboration"""
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
    
    # Team collaboration fields (new)
    owner: Optional[str] = None
    reviewer: Optional[str] = None
    status: str = 'todo'
    due_at: Optional[str] = None
    handoff_note: Optional[str] = None
    blocked_by: List[int] = field(default_factory=list)
    incident: bool = False

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
            'time_logs': self.time_logs,
            # Team collaboration fields
            'owner': self.owner,
            'reviewer': self.reviewer,
            'status': self.status,
            'due_at': self.due_at,
            'handoff_note': self.handoff_note,
            'blocked_by': self.blocked_by,
            'incident': self.incident,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create task from dictionary (handles old tasks safely with backward compatibility)"""
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
            time_logs=data.get('time_logs', []),
            # Team collaboration fields with safe defaults
            owner=data.get('owner'),
            reviewer=data.get('reviewer'),
            status=data.get('status', 'todo'),
            due_at=data.get('due_at'),
            handoff_note=data.get('handoff_note'),
            blocked_by=data.get('blocked_by', []),
            incident=data.get('incident', False),
        )

    def mark_done(self):
        """Mark task as completed with timestamp"""
        self.completed = True
        self.status = 'done'
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

    # Team collaboration helper methods
    def is_blocked(self) -> bool:
        """Check if task is blocked by other tasks"""
        return len(self.blocked_by) > 0

    def set_blocked_by(self, task_ids: List[int]):
        """Set which tasks block this one"""
        self.blocked_by = task_ids
        if task_ids:
            self.status = 'blocked'

    def add_blocker(self, task_id: int):
        """Add a task that blocks this one"""
        if task_id not in self.blocked_by and task_id != self.id:
            self.blocked_by.append(task_id)
            self.status = 'blocked'

    def remove_blocker(self, task_id: int):
        """Remove a blocking task"""
        if task_id in self.blocked_by:
            self.blocked_by.remove(task_id)
            if not self.blocked_by and self.status == 'blocked':
                self.status = 'todo'

    def is_overdue(self) -> bool:
        """Check if task is past its due date and not completed"""
        if not self.due_at or self.completed:
            return False
        try:
            due_date = datetime.fromisoformat(self.due_at).date()
            today = datetime.now().date()
            return due_date < today
        except (ValueError, TypeError):
            return False

    def is_due_soon(self, days: int = 1) -> bool:
        """Check if task is due within N days (default: 1 day)"""
        if not self.due_at or self.completed:
            return False
        try:
            due_date = datetime.fromisoformat(self.due_at).date()
            today = datetime.now().date()
            soon_date = today + timedelta(days=days)
            return today <= due_date <= soon_date
        except (ValueError, TypeError):
            return False

    def needs_handoff(self) -> bool:
        """Check if task needs handoff note (blocked but no note, or due soon without note)"""
        if self.completed:
            return False
        # Blocked tasks should have handoff notes
        if self.is_blocked() and not self.handoff_note:
            return True
        # Cross-person collaboration needs reviewer
        if self.owner and not self.reviewer and self.status == 'review':
            return True
        return False

    def has_owner(self) -> bool:
        """Check if task has an owner assigned"""
        return self.owner is not None and self.owner.strip() != ""

    def has_reviewer(self) -> bool:
        """Check if task has a reviewer assigned"""
        return self.reviewer is not None and self.reviewer.strip() != ""

    def is_incident_task(self) -> bool:
        """Check if this is an incident task"""
        return self.incident

    def set_status(self, new_status: str):
        """Set task status with validation"""
        if new_status not in STATUS_CHOICES:
            raise ValueError(f"Invalid status. Must be one of: {STATUS_CHOICES}")
        # If marking as done, also mark completed
        if new_status == 'done' and not self.completed:
            self.mark_done()
        else:
            self.status = new_status
            # If reactivating a done task
            if self.completed and new_status != 'done':
                self.completed = False
                self.completed_at = None

    def get_status_color(self) -> str:
        """Get Rich color for status display"""
        status_colors = {
            'todo': 'dim',
            'in_progress': 'cyan',
            'review': 'yellow',
            'blocked': 'red',
            'done': 'green',
        }
        return status_colors.get(self.status, 'dim')

    def get_due_date_display(self) -> str:
        """Get formatted due date with status indicator"""
        if not self.due_at:
            return "-"
        try:
            due = datetime.fromisoformat(self.due_at)
            due_str = due.strftime('%Y-%m-%d')
            if self.is_overdue():
                return f"[red]OVERDUE: {due_str}[/red]"
            elif self.is_due_soon():
                return f"[yellow]Soon: {due_str}[/yellow]"
            return due_str
        except (ValueError, TypeError):
            return str(self.due_at)
