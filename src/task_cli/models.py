from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import random
import string

def generate_task_id():
    letter = random.choice(string.ascii_lowercase)
    numbers = random.randint(0, 99)
    return f"{letter}{numbers:02d}"   # ensures two digits like 01, 09

class TaskStatus(str, Enum):
    DO = "do"
    DOING = "doing"
    DONE = "done"

class Priority(str, Enum):
    LOW = "low"
    MED = "med"
    HIGH = "high"

@dataclass
class Task:
    id: str = field(default_factory=generate_task_id)
    description: str = ""
    status: TaskStatus = TaskStatus.DO
    priority: Priority = Priority.LOW
    tags: List[str] = field(default_factory=list)
    project: Optional[str] = None
    due: Optional[str] = None
    recur: Optional[str] = None
    wait: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    total_duration: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "tags": self.tags,
            "project": self.project,
            "due": self.due,
            "recur": self.recur,
            "wait": self.wait,
            "subtasks": self.subtasks,
            "start_time": self.start_time,
            "total_duration": self.total_duration,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data.get("id"),
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "do")),
            priority=Priority(data.get("priority", "low")),
            tags=data.get("tags", []),
            project=data.get("project"),
            due=data.get("due"),
            recur=data.get("recur"),
            wait=data.get("wait"),
            subtasks=data.get("subtasks", []),
            start_time=data.get("start_time"),
            total_duration=data.get("total_duration", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )