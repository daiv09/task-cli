from typing import List, Optional
from datetime import datetime
from .models import Task, TaskStatus, Priority
from .repository import TaskRepository
from .utils import extract_tags, calculate_next_recurrence

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

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> Optional[Task]:
        tasks = self.repository.load_tasks()
        for task in tasks:
            if task.id == task_id:
                task.status = new_status
                task.updated_at = datetime.now().isoformat()
                
                # Check for recurrence if marked done
                if new_status == TaskStatus.DONE and task.recur:
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
        }
        return stats
