import sys
from datetime import datetime
from rich.console import Console
from rich.table import Table
from .models import Task, TaskStatus, Priority

console = Console()

def safe_char(char: str, fallback: str) -> str:
    try:
        char.encode(sys.stdout.encoding or "ascii")
        return char
    except Exception:
        return fallback

TICK = safe_char("✔", "v")
WARN = safe_char("⚠️", "!")
CROSS = safe_char("❌", "x")
BRANCH = safe_char("┗", " -")

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
