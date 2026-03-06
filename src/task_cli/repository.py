import json
import subprocess
from pathlib import Path
from typing import List
from .models import Task
from .config import DEFAULT_FILE_PATH

class TaskRepository:
    def __init__(self, file_path: Path = DEFAULT_FILE_PATH):
        self.file_path = file_path

    def _ensure_file_exists(self):
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def load_tasks(self) -> List[Task]:
        self._ensure_file_exists()
        try:
            content = self.file_path.read_text()
            data = json.loads(content)
            return [Task.from_dict(item) for item in data]
        except (json.JSONDecodeError, ValueError):
            return []

    def save_tasks(self, tasks: List[Task]):
        self._ensure_file_exists()
        data = [task.to_dict() for task in tasks]
        self.file_path.write_text(json.dumps(data, indent=2))

    def export_tasks(self, path: Path, format: str = "json"):
        tasks = self.load_tasks()
        if format == "json":
            data = [task.to_dict() for task in tasks]
            path.write_text(json.dumps(data, indent=2))
        elif format == "md":
            lines = ["# Tasks Export\n"]
            for t in tasks:
                status_icon = "x" if t.status == "done" else " "
                lines.append(f"- [{status_icon}] {t.description} (ID: {t.id}, Status: {t.status.value})")
            path.write_text("\n".join(lines))

    def import_tasks(self, path: Path):
        content = path.read_text()
        data = json.loads(content)
        imported = [Task.from_dict(item) for item in data]
        current = self.load_tasks()
        # Simple merge: append imported
        current.extend(imported)
        self.save_tasks(current)

    def execute_hook(self, hook_name: str, task: Task):
        hook_path = Path.home() / ".task-cli" / "hooks" / hook_name
        if hook_path.exists() and hook_path.is_file():
            try:
                # Pass task as JSON string to hook script
                subprocess.Popen(
                    [str(hook_path)], 
                    env={"TASK_JSON": json.dumps(task.to_dict())},
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
