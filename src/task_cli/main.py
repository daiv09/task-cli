import typer
from rich.console import Console
from rich.table import Table
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from .models import TaskStatus, Priority, Task
from .service import TaskService
from .config import VERSION, settings
from .utils import parse_date
from .clipboard import get_clipboard_text
import shlex
import pyperclip # verify presence for error handling in clip command

app = typer.Typer(help="Advanced CLI Task Manager", context_settings={"help_option_names": ["-h", "--help"]})
console = Console()
err_console = Console(stderr=True)
service = TaskService()


def format_date(iso_date: str) -> str:
    if not iso_date:
        return ""
    return iso_date[:10]  # Just YYYY-MM-DD for cleaner tables


def print_tasks(tasks: list[Task]):
    if not tasks:
        console.print("[dim]No tasks found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="bold cyan", width=8)
    table.add_column("Description", min_width=20)
    table.add_column("Status", width=6)
    table.add_column("Pri", width=4)
    table.add_column("Project", style="dim", width=10)
    table.add_column("Tags", style="dim", width=15)
    table.add_column("Due", width=10)

    status_colors = {
        TaskStatus.DO: "[red]do[/red]",
        TaskStatus.DOING: "[yellow]doing[/yellow]",
        TaskStatus.DONE: "[green]done[/green]",
    }
    
    priority_colors = {
        Priority.HIGH: "[red]high[/red]",
        Priority.MED: "[yellow]med[/yellow]",
        Priority.LOW: "[dim]low[/dim]",
    }

    now_iso = datetime.now().isoformat()

    for task in tasks:
        status_text = status_colors.get(task.status, task.status.value)
        pri_text = priority_colors.get(task.priority, task.priority.value)
        
        # Add running indicator
        desc_text = task.description
        if task.start_time:
            status_text = "[green]running[/green]"

        due_text = format_date(task.due)
        if task.due and task.due < now_iso and task.status != TaskStatus.DONE:
            due_text = f"[bold red]{due_text}[/bold red]"

        tags_text = ", ".join(task.tags) if task.tags else ""
        proj_text = task.project or ""

        table.add_row(
            task.id,
            desc_text,
            status_text,
            pri_text,
            proj_text,
            tags_text,
            due_text
        )
        
        # Add subtasks
        for sub in task.subtasks:
            table.add_row(
                "",
                f"  ┗ [dim]{sub}[/dim]",
                "", "", "", "", ""
            )

    console.print(table)
    console.print()

@app.command()
def quick(
    description: str = typer.Argument(..., help="Quickly add a high-priority task")
):
    """Create a high-priority task instantly"""

    service.repository.save_backup()

    task = service.add_task(
        description=description,
        priority=Priority.HIGH,
        project=settings.default_project,
        due=None,
        recur=None,
        wait=None
    )

    console.print(
        f"[green]✔ Created[/green] high priority task [bold]{task.id}[/bold]"
    )

def resolve_id(short_id: str) -> str:
    tasks = service.list_tasks(include_waiting=True)
    matches = [t.id for t in tasks if t.id.startswith(short_id)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        err_console.print(f"[red]Error:[/red] Short ID '{short_id}' is ambiguous. Matches: {', '.join(m[:8] for m in matches)}")
        raise typer.Exit(code=1)
    return short_id


@app.command(name="add")
def add_task(
    description: str = typer.Argument(..., help="Description of the task (+tags supported)"),
    priority: Priority = typer.Option(Priority.LOW, "--priority", "-p", help="Task priority"),
    project: Optional[str] = typer.Option(None, "--project", help="Assign to project"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (YYYY-MM-DD)"),
    recur: Optional[str] = typer.Option(None, "--recur", help="Recurrence (daily, weekly, etc)"),
    wait: Optional[str] = typer.Option(None, "--wait", help="Hide until date (YYYY-MM-DD)")
):
    """Create a new task"""
    try:
        due_iso = parse_date(due) if due else None
        wait_iso = parse_date(wait) if wait else None
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    # Use default project from config if none provided
    if not project and settings.default_project:
        project = settings.default_project

    service.repository.save_backup()
    task = service.add_task(
        description=description,
        priority=priority,
        project=project,
        due=due_iso,
        recur=recur,
        wait=wait_iso
    )
    console.print(f"[green]✔ Created[/green] task [bold]{task.id}[/bold]")

@app.command(name="a", hidden=True)
def add_alias(
    description: str = typer.Argument(...),
    priority: Priority = typer.Option(Priority.LOW, "--priority", "-p"),
    project: Optional[str] = typer.Option(None, "--project"),
    due: Optional[str] = typer.Option(None, "--due"),
    recur: Optional[str] = typer.Option(None, "--recur"),
    wait: Optional[str] = typer.Option(None, "--wait")
):
    add_task(description, priority, project, due, recur, wait)


@app.command(name="list")
def list_tasks(
    status: Optional[TaskStatus] = typer.Argument(None, help="Filter by status"),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    project: Optional[str] = typer.Option(None, "--project", help="Filter by project"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    sort: Optional[str] = typer.Option(None, "--sort", help="Sort by (priority, due, created)"),
    before: Optional[str] = typer.Option(None, "--before", help="Due before (YYYY-MM-DD)"),
    after: Optional[str] = typer.Option(None, "--after", help="Due after (YYYY-MM-DD)"),
    all: bool = typer.Option(False, "--all", help="Include waiting/hidden tasks"),
    overdue: bool = typer.Option(False, "--overdue", help="Show only overdue tasks")
):
    """List all tasks"""
    try:
        before_iso = parse_date(before) if before else None
        after_iso = parse_date(after) if after else None
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    if overdue:
        before_iso = datetime.now().isoformat()
        status = status or TaskStatus.DO  # Only show undone by default

    # If context is active, force tag filter
    if settings.context and not tag:
        tag = settings.context

    tasks = service.list_tasks(
        status=status,
        priority=priority,
        project=project,
        tag=tag,
        sort_by=sort,
        before=before_iso,
        after=after_iso,
        include_waiting=all
    )
    print_tasks(tasks)

@app.command(name="ls", hidden=True)
def list_alias(
    status: Optional[TaskStatus] = typer.Argument(None),
    priority: Optional[Priority] = typer.Option(None, "--priority", "-p"),
    project: Optional[str] = typer.Option(None, "--project"),
    tag: Optional[str] = typer.Option(None, "--tag"),
    sort: Optional[str] = typer.Option(None, "--sort"),
    before: Optional[str] = typer.Option(None, "--before"),
    after: Optional[str] = typer.Option(None, "--after"),
    all: bool = typer.Option(False, "--all"),
    overdue: bool = typer.Option(False, "--overdue")
):
    list_tasks(status, priority, project, tag, sort, before, after, all, overdue)


@app.command()
def update(
    task_id: str, 
    new_description: Optional[str] = typer.Argument(
        None, 
        help="The new description for the task (Optional)"
    ),
    priority: Optional[str] = typer.Option(
        None, "--priority", "-p", help="Update priority (low, med, high)"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", help="Change the project name"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Change status (do, doing, done)"
    )
):
    """Update a task's description, metadata, or cycle its status."""

    task_id = resolve_id(task_id)

    # Check if task exists
    task = service.get_task(task_id)
    if not task:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)

    # If NO update parameters provided → cycle status
    if not any([new_description, priority, project, status]):

        if task.status == TaskStatus.DO:
            new_status = TaskStatus.DOING
        elif task.status == TaskStatus.DOING:
            new_status = TaskStatus.DONE
        else:
            new_status = TaskStatus.DO

        service.update_task_status(task_id, new_status)

        status_color = {
            TaskStatus.DO: "red",
            TaskStatus.DOING: "yellow",
            TaskStatus.DONE: "green"
        }

        console.print(
            f"[green]✔ Updated[/green] task [bold]{task.id}[/bold] → "
            f"[{status_color[new_status]}]{new_status.value}[/{status_color[new_status]}]"
        )
        return

    service.repository.save_backup()

    # Otherwise perform standard updates
    if new_description:
        service.update_task_description(task_id, new_description)

    if priority:
        service.update_task_priority(task_id, priority)

    if project:
        service.update_task_project(task_id, project)

    if status:
        service.update_task_status(task_id, status)

    console.print(
        f"[green]✔ Updated[/green] task [bold]{task.id}[/bold]"
    )

def _mark_task(task_id: str, status: TaskStatus):
    task_id = resolve_id(task_id)
    task = service.update_task_status(task_id, status)
    if task:
        console.print(f"Task {task_id[:8]} is now {status.value}")
    else:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)


@app.command()
def mark_doing(task_id: str):
    """Change status to doing"""
    _mark_task(task_id, TaskStatus.DOING)

@app.command()
def mark_done(task_id: str):
    """Change status to done"""
    _mark_task(task_id, TaskStatus.DONE)

@app.command()
def mark_do(task_id: str):
    """Change status to do"""
    _mark_task(task_id, TaskStatus.DO)

@app.command()
def delete(task_id: str):
    """Delete a task"""
    task_id = resolve_id(task_id)
    success = service.delete_task(task_id)
    if success:
        console.print(f"[green]✔ Deleted[/green] task [bold]{task_id}[/bold]")
    else:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)

@app.command()
def done(task_id: str):
    """Mark a task as done"""
    task_id = resolve_id(task_id)
    task = service.update_task_status(task_id, TaskStatus.DONE)

    if not task:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✔ Completed[/green] task [bold]{task_id}[/bold]")

@app.command()
def clear():
    """Delete all tasks"""
    
    confirm = typer.confirm("Are you sure you want to delete ALL tasks?")
    if not confirm:
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit()

    service.repository.clear_tasks()

    console.print("[green]✔ All tasks cleared.[/green]")

# === NEW COMMANDS ===

@app.command()
def today():
    """Show tasks due today or overdue"""
    iso_today = datetime.now().replace(hour=23, minute=59, second=59).isoformat()
    tasks = service.list_tasks(before=iso_today, sort_by="priority")
    # Exclude done
    tasks = [t for t in tasks if t.status != TaskStatus.DONE]
    console.print("[bold cyan]Tasks for Today[/bold cyan]")
    print_tasks(tasks)

@app.command()
def next():
    """Show top 5 most important tasks"""
    tasks = service.list_tasks(sort_by="priority")
    # Exclude done
    tasks = [t for t in tasks if t.status != TaskStatus.DONE]
    
    # Sort secondarily by due date if available
    def next_sort_key(t):
        pri_val = {"high": 0, "med": 1, "low": 2}.get(t.priority.value, 3)
        due_val = t.due if t.due else "9999-12-31"
        return (pri_val, due_val)
        
    tasks.sort(key=next_sort_key)
    print_tasks(tasks[:5])

@app.command()
def focus():
    """Focus mode - show a single next task"""
    tasks = service.list_tasks(status=TaskStatus.DOING)
    if not tasks:
        # Get highest priority DO task
        all_do = service.list_tasks(status=TaskStatus.DO, sort_by="priority")
        if all_do:
            tasks = [all_do[0]]
            
    if tasks:
        task = tasks[0]
        console.rule(f"[bold cyan] Focus: {task.id} ")
        console.print(f"Priority: {task.priority.value} | Due: {format_date(task.due) or 'None'}")
        console.print(f"[bold white]{task.description}[/bold white]")
    else:
        console.print("No actionable tasks available to focus on.")

@app.command()
def context(tag: str = typer.Argument(None, help="Tag to focus on, or 'none' to clear")):
    """Set active context for all commands"""
    config_path = Path.home() / ".task-cli.context"
    if tag and tag.lower() != "none":
        config_path.write_text(tag)
        console.print(f"Context set to '[cyan]{tag}[/cyan]'. Run `t context none` to clear.")
    else:
        if config_path.exists():
            config_path.unlink()
        console.print("Context cleared.")

@app.command()
def export(file: Path, format: str = typer.Option("json", "--format", help="json or md")):
    """Export tasks to a file"""
    service.repository.export_tasks(file, format)
    console.print(f"Tasks exported to {file} as {format}.")

@app.command()
def import_tasks(file: Path):
    """Import tasks from a JSON file"""
    if not file.exists():
        err_console.print(f"[red]Error: File {file} does not exist.[/red]")
        raise typer.Exit(code=1)
    service.repository.import_tasks(file)
    console.print(f"Tasks imported successfully from {file}.")

@app.command()
def stats():
    """Show task statistics"""
    s = service.get_stats()
    table = Table(title="Task Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    def format_duration(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0: return f"{h}h {m}m"
        if m > 0: return f"{m}m {s}s"
        return f"{s}s"

    table.add_row("Total Time", format_duration(s["total_time"]))
    table.add_row("Avg Task Duration", format_duration(s["avg_duration"]))
    
    console.print(table)

@app.command()
def search(keyword: str):
    """Search tasks by keyword in description, project, or tags."""
    results = service.search(keyword)
    console.print(f"Search results for '[bold cyan]{keyword}[/bold cyan]':")
    print_tasks(results)

@app.command()
def undo():
    """Undo the last destructive operation."""
    if service.undo_last():
        console.print("[green]✔ Last operation undone successfully.[/green]")
    else:
        err_console.print("[red]Error: Nothing to undo or backup not found.[/red]")
        raise typer.Exit(code=1)

@app.command()
def archive():
    """Move all completed tasks to archive file."""
    service.archive_done_tasks()
    console.print("[green]✔ Completed tasks archived to ~/.task-cli/archive.json[/green]")

@app.command()
def clip():
    """Create a task from clipboard text."""
    text = get_clipboard_text()
    if not text:
        err_console.print("[red]Error: Clipboard is empty.[/red]")
        raise typer.Exit(code=1)
    
    service.repository.save_backup()
    task = service.add_task(description=text)
    console.print(f"[green]✔ Created task from clipboard:[/green] [bold]{task.id}[/bold]")

@app.command()
def sub(task_id: str, description: str):
    """Add a subtask to an existing task."""
    task_id = resolve_id(task_id)
    service.repository.save_backup()
    task = service.add_subtask(task_id, description)
    if task:
        console.print(f"[green]✔ Added subtask to[/green] [bold]{task_id[:8]}[/bold]")
    else:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)

@app.command()
def start(task_ref: str = typer.Argument(..., help="Task ID or new task description")):
    """Start tracking time for a task. Creates a new task if description is provided."""

    tasks = service.list_tasks(include_waiting=True)
    matches = [t for t in tasks if t.id.startswith(task_ref)]

    service.repository.save_backup()

    # Existing task
    if len(matches) == 1:
        task = service.start_time_tracking(task_id=matches[0].id)

        console.print(
            f"[green]▶ Started[/green] task "
            f"[bold cyan]{task.id}[/bold cyan]  "
            f"[dim]{task.description}[/dim]"
        )

    # Ambiguous ID
    elif len(matches) > 1:
        ids = ", ".join(t.id for t in matches)
        err_console.print(
            f"[red]Error:[/red] Task reference is ambiguous. Matches: {ids}"
        )
        raise typer.Exit(1)

    # Create new task
    else:
        task = service.start_time_tracking(description=task_ref)

        console.print(
            f"[green]✔ Created + Started[/green] task "
            f"[bold cyan]{task.id}[/bold cyan]  "
            f"[dim]{task.description}[/dim]"
        )

@app.command()
def stop(task_id: Optional[str] = typer.Argument(None, help="Task ID (optional)")):
    """Stop time tracking."""

    task = service.stop_time_tracking(task_id)

    if not task:
        console.print("[yellow]No active task currently being tracked.[/yellow]")
        return

    duration = task.total_duration
    seconds = int(duration)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        time_text = f"{hours}h {minutes}m"
    elif minutes > 0:
        time_text = f"{minutes}m {seconds}s"
    else:
        time_text = f"{seconds}s"

    console.print(
        f"[green]■ Stopped[/green] task "
        f"[bold cyan]{task.id}[/bold cyan]  "
        f"[dim]{task.description}[/dim]\n"
        f"[bold]Time spent:[/bold] {time_text}"
    )   

@app.command()
def dashboard():
    """Display high-level dashboard of tasks."""
    s = service.get_stats()
    iso_today = datetime.now().replace(hour=23, minute=59, second=59).isoformat()
    tasks_today = service.list_tasks(before=iso_today)
    tasks_today = [t for t in tasks_today if t.status != TaskStatus.DONE]
    
    overdue_tasks = [t for t in tasks_today if t.due and t.due < datetime.now().isoformat()]
    
    console.print(f"[bold cyan]DASHBOARD - {datetime.now().strftime('%Y-%m-%d %H:%M')}[/bold cyan]")
    
    # Summary Table
    sum_table = Table(box=None)
    sum_table.add_column("Stat", style="bold")
    sum_table.add_column("Value")
    sum_table.add_row("Total Tasks", str(s["total"]))
    sum_table.add_row("Due Today", f"[yellow]{len(tasks_today)}[/yellow]")
    sum_table.add_row("Overdue", f"[red]{len(overdue_tasks)}[/red]")
    console.print(sum_table)

    # Top 5 Priorities
    console.print("\n[bold]Top Priorities:[/bold]")
    next()

    # Focus Task
    console.print("\n[bold]Focus:[/bold]")
    focus()

@app.command()
def shell():
    """Start interactive task shell."""
    console.print("[bold green]Task CLI Interactive Shell[/bold green]")
    console.print("Type 'exit' or 'quit' to leave.")
    
    import sys
    while True:
        try:
            line = console.input("[bold cyan]task> [/bold cyan]").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit"):
                break
            
            # Use shlex to split preserving quotes
            cmd_args = shlex.split(line)
            # Invoke typer app
            try:
                # We need to call the app with the specific arguments
                # Since Typer doesn't have a direct 'invoke' that takes a list easily without re-parsing
                # We can use the main app's internal behavior or just wrap it.
                # A simple way for a basic REPL:
                import subprocess
                # Run the actual 't' command
                subprocess.run(["t"] + cmd_args)
            except Exception as e:
                console.print(f"[red]Error executing command:[/red] {e}")
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit.[/yellow]")


def version_callback(value: bool):
    if value:
        console.print(f"Task CLI Version: [bold]{VERSION}[/bold]")
        raise typer.Exit()

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True, help="Show the version and exit."
    )
):
    """
    Advanced Task Tracker CLI
    """
    # Load context if exists
    ctx_path = Path.home() / ".task-cli.context"
    if ctx_path.exists():
        settings.context = ctx_path.read_text().strip()

if __name__ == "__main__":
    app()
