from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

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
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    status: TaskStatus = TaskStatus.DO
    priority: Priority = Priority.LOW
    tags: List[str] = field(default_factory=list)
    project: Optional[str] = None
    due: Optional[str] = None
    recur: Optional[str] = None
    wait: Optional[str] = None
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
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
