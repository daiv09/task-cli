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
        
        due_text = format_date(task.due)
        if task.due and task.due < now_iso and task.status != TaskStatus.DONE:
            due_text = f"[bold red]{due_text}[/bold red]"

        tags_text = ", ".join(task.tags) if task.tags else ""
        proj_text = task.project or ""

        table.add_row(
            task.id,
            task.description,
            status_text,
            pri_text,
            proj_text,
            tags_text,
            due_text
        )

    console.print(table)


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

    task = service.add_task(
        description=description,
        priority=priority,
        project=project,
        due=due_iso,
        recur=recur,
        wait=wait_iso
    )
    console.print(f"Created task {task.id} (do)")


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
def update(task_id: str, new_description: str):
    """Update a task description"""
    task = service.update_task_description(task_id, new_description)
    if task:
        console.print(f"Task {task_id} description updated.")
    else:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)


def _mark_task(task_id: str, status: TaskStatus):
    task = service.update_task_status(task_id, status)
    if task:
        console.print(f"Task {task_id} is now {status.value}")
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
    success = service.delete_task(task_id)
    if success:
        console.print(f"Task {task_id} deleted.")
    else:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)

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
        console.print(f"[bold cyan]Focused Task ({task.id})[/bold cyan]")
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
    
    table.add_row("Total Tasks", str(s["total"]))
    table.add_row("Status: Do", f"[red]{s['do']}[/red]")
    table.add_row("Status: Doing", f"[yellow]{s['doing']}[/yellow]")
    table.add_row("Status: Done", f"[green]{s['done']}[/green]")
    
    console.print(table)


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
