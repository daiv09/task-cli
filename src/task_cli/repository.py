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
        """Ensure the task storage file exists."""
        if not self.file_path.exists():
            self.file_path.write_text("[]")

    def load_tasks(self) -> List[Task]:
        """Load tasks from storage."""
        self._ensure_file_exists()

        try:
            content = self.file_path.read_text()
            data = json.loads(content)
            return [Task.from_dict(item) for item in data]

        except (json.JSONDecodeError, ValueError):
            return []

    def save_tasks(self, tasks: List[Task]):
        """Save tasks to storage."""
        self._ensure_file_exists()

        data = [task.to_dict() for task in tasks]
        self.file_path.write_text(json.dumps(data, indent=2))

    def clear_tasks(self):
        """Delete all tasks."""
        self.save_tasks([])

    def _backup_path(self) -> Path:
        """Path to the backup file in user's home directory."""
        return Path.home() / ".task-cli" / "backup.json"

    def save_backup(self):
        """Save current tasks to backup file for undo functionality."""
        backup_path = self._backup_path()
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        tasks = self.load_tasks()
        backup_path.write_text(json.dumps([t.to_dict() for t in tasks], indent=2))

    def load_backup(self) -> bool:
        """Load tasks from backup file, replacing current tasks. Returns True if successful."""
        backup_path = self._backup_path()
        if not backup_path.exists():
            return False
        try:
            data = json.loads(backup_path.read_text())
            tasks = [Task.from_dict(item) for item in data]
            self.save_tasks(tasks)
            return True
        except Exception:
            return False

    def _archive_path(self) -> Path:
        """Path to the archive file for completed tasks."""
        return Path.home() / ".task-cli" / "archive.json"

    def archive_completed(self):
        """Move all DONE tasks to archive file and remove them from active list."""
        archive_path = self._archive_path()
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        tasks = self.load_tasks()
        done_tasks = [t for t in tasks if t.status == TaskStatus.DONE]
        remaining = [t for t in tasks if t.status != TaskStatus.DONE]
        # Append to archive file
        if archive_path.exists():
            try:
                existing = json.loads(archive_path.read_text())
            except Exception:
                existing = []
        else:
            existing = []
        existing.extend([t.to_dict() for t in done_tasks])
        archive_path.write_text(json.dumps(existing, indent=2))
        # Save remaining tasks back
        self.save_tasks(remaining)

    def export_tasks(self, path: Path, format: str = "json"):
        """Export tasks to JSON or Markdown."""
        tasks = self.load_tasks()

        if format == "json":
            data = [task.to_dict() for task in tasks]
            path.write_text(json.dumps(data, indent=2))

        elif format == "md":
            lines = ["# Tasks Export\n"]

            for t in tasks:
                status_icon = "x" if t.status.value == "done" else " "
                lines.append(
                    f"- [{status_icon}] {t.description} "
                    f"(ID: {t.id}, Status: {t.status.value})"
                )

            path.write_text("\n".join(lines))

    def import_tasks(self, path: Path):
        """Import tasks from a JSON file."""
        content = path.read_text()
        data = json.loads(content)

        imported_tasks = [Task.from_dict(item) for item in data]

        current_tasks = self.load_tasks()
        current_tasks.extend(imported_tasks)

        self.save_tasks(current_tasks)

    def execute_hook(self, hook_name: str, task: Task):
        """Execute a hook script if present."""
        hook_path = Path.home() / ".task-cli" / "hooks" / hook_name

        if hook_path.exists() and hook_path.is_file():
            try:
                subprocess.Popen(
                    [str(hook_path)],
                    env={"TASK_JSON": json.dumps(task.to_dict())},
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            except Exception:
                pass