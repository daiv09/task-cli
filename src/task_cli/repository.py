import json
import subprocess
from pathlib import Path
from typing import List
from datetime import datetime

from .models import Task
from .config import DEFAULT_FILE_PATH

class TaskRepository:
    def __init__(self, file_path: Path = DEFAULT_FILE_PATH):
        self.file_path = file_path
        self.db_path = self.file_path.with_suffix(".db")
        self._init_db()

    def _ensure_file_exists(self):
        """Ensure the parent directory of the DB exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        import sqlite3
        self._ensure_file_exists()
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    status TEXT,
                    priority TEXT,
                    tags TEXT,
                    project TEXT,
                    due TEXT,
                    recur TEXT,
                    wait TEXT,
                    subtasks TEXT,
                    start_time TEXT,
                    total_duration INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _migrate_if_needed(self):
        import sys
        # print(f"DEBUG: _migrate_if_needed check: path={self.file_path}, exists={self.file_path.exists()}", file=sys.stderr, flush=True)
        if self.file_path.exists() and self.file_path.is_file():
            import typer
            # Try to load tasks from JSON
            try:
                content = self.file_path.read_text(encoding="utf-8")
                if not content.strip():
                    data = []
                else:
                    data = json.loads(content)
                tasks = [Task.from_dict(item) for item in data]
                print(f"DEBUG: migration parsed tasks: {tasks}", file=sys.stderr, flush=True)
            except json.JSONDecodeError as e:
                print(f"Error: Storage file {self.file_path} is corrupted (invalid JSON). Details: {e}", file=sys.stderr)
                raise typer.Exit(code=1)
            except Exception:
                tasks = []

            # Save to SQLite
            self.save_tasks(tasks)
            
            # Remove tasks.json
            try:
                self.file_path.unlink()
            except Exception:
                pass

    def load_tasks(self) -> List[Task]:
        """Load tasks from SQLite storage."""
        self._init_db()
        self._migrate_if_needed()
        
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, description, status, priority, tags, project, due, recur, wait, subtasks, start_time, total_duration, created_at, updated_at
                FROM tasks
            """)
            rows = cursor.fetchall()
            tasks = []
            for r in rows:
                tags = json.loads(r[4]) if r[4] else []
                subtasks = json.loads(r[9]) if r[9] else []
                
                # Try to map status/priority if they are strings
                from .models import TaskStatus, Priority
                status_val = TaskStatus(r[2]) if r[2] else TaskStatus.DO
                priority_val = Priority(r[3]) if r[3] else Priority.LOW
                
                tasks.append(Task(
                    id=r[0],
                    description=r[1],
                    status=status_val,
                    priority=priority_val,
                    tags=tags,
                    project=r[5],
                    due=r[6],
                    recur=r[7],
                    wait=r[8],
                    subtasks=subtasks,
                    start_time=r[10],
                    total_duration=r[11] or 0,
                    created_at=r[12],
                    updated_at=r[13]
                ))
            return tasks
        except Exception as e:
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn.close()

    def save_tasks(self, tasks: List[Task]):
        """Save tasks to SQLite storage."""
        import sqlite3
        self._ensure_file_exists()
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks")
            for t in tasks:
                cursor.execute("""
                    INSERT INTO tasks (id, description, status, priority, tags, project, due, recur, wait, subtasks, start_time, total_duration, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    t.id,
                    t.description,
                    t.status.value if hasattr(t.status, "value") else t.status,
                    t.priority.value if hasattr(t.priority, "value") else t.priority,
                    json.dumps(t.tags),
                    t.project,
                    t.due,
                    t.recur,
                    t.wait,
                    json.dumps(t.subtasks),
                    t.start_time,
                    t.total_duration,
                    t.created_at,
                    t.updated_at
                ))
            conn.commit()
        finally:
            conn.close()

    def clear_tasks(self):
        """Delete all tasks."""
        self.save_tasks([])

    def _history_path(self) -> Path:
        """Path to the history.jsonl file."""
        return Path.home() / ".task-cli" / "history.jsonl"

    def save_backup(self, op: str = "operation", task_id: str = ""):
        """Append the current state of tasks to history.jsonl."""
        history_path = self._history_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load current tasks (snapshot before the operation)
        tasks = self.load_tasks()
        snapshot = [t.to_dict() for t in tasks]
        
        # Read existing history entries
        entries = []
        if history_path.exists():
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
            except Exception:
                pass
        
        # Create new entry
        new_entry = {
            "op": op,
            "task_id": task_id,
            "snapshot": snapshot,
            "ts": datetime.now().isoformat()
        }
        entries.append(new_entry)
        
        # Keep only the last 20 entries
        entries = entries[-20:]
        
        # Write back to history.jsonl
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def load_backup(self) -> bool:
        """Pop the last history entry and restore tasks from its snapshot. Returns True if successful."""
        history_path = self._history_path()
        if not history_path.exists():
            return False
            
        entries = []
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception:
            return False
            
        if not entries:
            return False
            
        # Pop the last entry
        last_entry = entries.pop()
        
        # Restore task state from snapshot
        try:
            tasks_data = last_entry["snapshot"]
            tasks = [Task.from_dict(t) for t in tasks_data]
            self.save_tasks(tasks)
        except Exception:
            return False
            
        # Write remaining entries back
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
            
        return True

    def _archive_path(self) -> Path:
        """Path to the archive file for completed tasks."""
        return Path.home() / ".task-cli" / "archive.json"

    def archive_completed(self):
        """Move all DONE tasks to archive file and remove them from active list."""
        from .models import TaskStatus
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