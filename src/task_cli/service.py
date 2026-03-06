from typing import List, Optional
from datetime import datetime
from .models import Task, TaskStatus, Priority
from .repository import TaskRepository
from .utils import extract_tags, calculate_next_recurrence
from .nlp_dates import parse_natural_date

class TaskService:
    def __init__(self, repository: TaskRepository = None):
        self.repository = repository or TaskRepository()

    def add_task(
        self, 
        description: str,
        priority: Priority = Priority.LOW,
        project: Optional[str] = None,
        due: Optional[str] = None,
        recur: Optional[str] = None,
        wait: Optional[str] = None
    ) -> Task:
        # Check for natural language dates
        clean_desc, nlp_due = parse_natural_date(description)
        if nlp_due and not due:
            due = nlp_due
            description = clean_desc

        tasks = self.repository.load_tasks()
        
        # Extract tags from description
        clean_desc, desc_tags = extract_tags(description)

        new_task = Task(
            description=clean_desc,
            priority=priority,
            tags=desc_tags,
            project=project,
            due=due,
            recur=recur,
            wait=wait
        )
        tasks.append(new_task)
        self.repository.save_tasks(tasks)
        self.repository.execute_hook("on-add", new_task)
        return new_task

    def list_tasks(
        self, 
        status: Optional[TaskStatus] = None,
        priority: Optional[Priority] = None,
        project: Optional[str] = None,
        tag: Optional[str] = None,
        sort_by: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        include_waiting: bool = False
    ) -> List[Task]:
        tasks = self.repository.load_tasks()
        now_iso = datetime.now().isoformat()
        filtered = []
        
        for t in tasks:
            # Hide waiting tasks by default
            if not include_waiting and t.wait and t.wait > now_iso:
                continue
                
            if status and t.status != status:
                continue
            if priority and t.priority != priority:
                continue
            if project and t.project != project:
                continue
            if tag and tag not in t.tags:
                continue
            if before and t.due and t.due >= before:
                continue
            if after and t.due and t.due <= after:
                continue
                
            filtered.append(t)

        if sort_by == "priority":
            priorities = {Priority.HIGH: 0, Priority.MED: 1, Priority.LOW: 2}
            filtered.sort(key=lambda x: priorities.get(x.priority, 99))
        elif sort_by == "created":
            filtered.sort(key=lambda x: x.created_at)
        elif sort_by == "due":
            # Put tasks with no due date at the end
            filtered.sort(key=lambda x: x.due or "9999-12-31")
            
        return filtered

    def get_task(self, task_id: str) -> Optional[Task]:
        tasks = self.repository.load_tasks()
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def search(self, keyword: str) -> List[Task]:
        """Search tasks by keyword in description, project, or tags."""
        tasks = self.repository.load_tasks()
        keyword = keyword.lower()
        results = []
        for t in tasks:
            if keyword in t.description.lower() or \
               (t.project and keyword in t.project.lower()) or \
               any(keyword in tag.lower() for tag in t.tags):
                results.append(t)
        return results

    def undo_last(self) -> bool:
        """Undo the last destructive operation."""
        return self.repository.load_backup()

    def archive_done_tasks(self):
        """Archive all completed tasks."""
        self.repository.archive_completed()

    def add_subtask(self, task_id: str, description: str) -> Optional[Task]:
        """Add a subtask to an existing task."""
        tasks = self.repository.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.subtasks.append(description)
                task.updated_at = datetime.now().isoformat()
                self.repository.save_tasks(tasks)
                return task
        return None

    def start_time_tracking(self, task_id: Optional[str] = None, description: Optional[str] = None) -> Optional[Task]:
        """Start time tracking for a task. If description is provided, create a NEW task."""
        tasks = self.repository.load_tasks()
        now_iso = datetime.now().isoformat()

        # Stop any currently running task
        for t in tasks:
            if t.start_time:
                start_dt = datetime.fromisoformat(t.start_time)
                now_dt = datetime.fromisoformat(now_iso)
                t.total_duration += int((now_dt - start_dt).total_seconds())
                t.start_time = None

        target_task = None
        if description:
            # Create and start new task
            clean_desc, desc_tags = extract_tags(description)
            target_task = Task(
                description=clean_desc,
                priority=Priority.MED,
                status=TaskStatus.DOING,
                tags=desc_tags,
                start_time=now_iso
            )
            tasks.append(target_task)
        elif task_id:
            # Start existing task
            for t in tasks:
                if t.id == task_id:
                    t.start_time = now_iso
                    t.status = TaskStatus.DOING
                    target_task = t
                    break

        if target_task:
            self.repository.save_tasks(tasks)
        return target_task

    def stop_time_tracking(self, task_id: Optional[str] = None) -> Optional[Task]:
        """Stop time tracking for a task (or the currently running one)."""
        tasks = self.repository.load_tasks()
        now_iso = datetime.now().isoformat()
        stopped_task = None

        for t in tasks:
            if (task_id and t.id == task_id and t.start_time) or (not task_id and t.start_time):
                start_dt = datetime.fromisoformat(t.start_time)
                now_dt = datetime.fromisoformat(now_iso)
                t.total_duration += int((now_dt - start_dt).total_seconds())
                t.start_time = None
                stopped_task = t
                break

        if stopped_task:
            self.repository.save_tasks(tasks)
        return stopped_task

    def update_task_description(self, task_id: str, new_description: str) -> Optional[Task]:
        tasks = self.repository.load_tasks()
        for task in tasks:
            if task.id == task_id:
                clean_desc, new_tags = extract_tags(new_description)
                task.description = clean_desc
                if new_tags:
                    task.tags.extend(new_tags)
                    task.tags = list(set(task.tags))
                task.updated_at = datetime.now().isoformat()
                self.repository.save_tasks(tasks)
                self.repository.execute_hook("on-update", task)
                return task
        return None

    def update_task_priority(self, task_id: str, new_priority: str) -> Optional[Task]:
        tasks = self.repository.load_tasks()
        try:
            priority_enum = Priority(new_priority)
        except ValueError:
            return None
        for task in tasks:
            if task.id == task_id:
                task.priority = priority_enum
                task.updated_at = datetime.now().isoformat()
                self.repository.save_tasks(tasks)
                self.repository.execute_hook("on-update", task)
                return task
        return None

    def update_task_project(self, task_id: str, new_project: str) -> Optional[Task]:
        tasks = self.repository.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.project = new_project
                task.updated_at = datetime.now().isoformat()
                self.repository.save_tasks(tasks)
                self.repository.execute_hook("on-update", task)
                return task
        return None

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> Optional[Task]:
        tasks = self.repository.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.status = new_status
                task.updated_at = datetime.now().isoformat()
                
                # Check for recurrence if marked done
                if new_status == TaskStatus.DONE:
                    # Stop tracking if it was running
                    if task.start_time:
                        start_dt = datetime.fromisoformat(task.start_time)
                        now_dt = datetime.fromisoformat(task.updated_at)
                        task.total_duration += int((now_dt - start_dt).total_seconds())
                        task.start_time = None

                    if task.recur:
                        next_due = calculate_next_recurrence(task.due or task.updated_at, task.recur)
                        if next_due:
                            new_task = Task(
                                description=task.description,
                                priority=task.priority,
                                tags=task.tags,
                                project=task.project,
                                due=next_due,
                                recur=task.recur
                            )
                            tasks.append(new_task)
                
                self.repository.save_tasks(tasks)
                if new_status == TaskStatus.DONE:
                    self.repository.execute_hook("on-done", task)
                else:
                    self.repository.execute_hook("on-update", task)
                    
                return task
        return None

    def delete_task(self, task_id: str) -> bool:
        tasks = self.repository.load_tasks()
        initial_count = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]
        if len(tasks) < initial_count:
            self.repository.save_tasks(tasks)
            return True
        return False

    def get_stats(self) -> dict:
        tasks = self.repository.load_tasks()
        stats = {
            "total": len(tasks),
            "do": sum(1 for t in tasks if t.status == TaskStatus.DO),
            "doing": sum(1 for t in tasks if t.status == TaskStatus.DOING),
            "done": sum(1 for t in tasks if t.status == TaskStatus.DONE),
            "total_time": sum(t.total_duration for t in tasks),
            "avg_duration": 0
        }
        completed_tasks = [t for t in tasks if t.total_duration > 0]
        if completed_tasks:
            stats["avg_duration"] = stats["total_time"] / len(completed_tasks)
        return stats
