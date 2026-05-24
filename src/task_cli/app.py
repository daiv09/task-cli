import typer
from rich.console import Console
from typing import List, Optional
from .models import TaskStatus
from .service import TaskService

app = typer.Typer(help="Advanced CLI Task Manager", context_settings={"help_option_names": ["-h", "--help"]})
ai_app = typer.Typer(help="Agentic & AI-powered Task CLI extensions", context_settings={"help_option_names": ["-h", "--help"]})
app.add_typer(ai_app, name="ai")

console = Console()
err_console = Console(stderr=True)
service = TaskService()

def complete_task_id(ctx: typer.Context, args: List[str], incomplete: str) -> List[str]:
    try:
        tasks = service.list_tasks(include_waiting=True)
        return [t.id for t in tasks if t.status != TaskStatus.DONE and t.id.startswith(incomplete)]
    except Exception:
        return []

def resolve_id(short_id: str) -> str:
    tasks = service.list_tasks(include_waiting=True)
    matches = [t.id for t in tasks if t.id.startswith(short_id)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        err_console.print(f"[red]Error:[/red] Short ID '{short_id}' is ambiguous. Matches: {', '.join(m[:8] for m in matches)}")
        raise typer.Exit(code=1)
    return short_id

def get_git_repo_name() -> Optional[str]:
    import os
    import sys
    if os.environ.get("TASK_DB_PATH") or "pytest" in sys.modules:
        return None
    import subprocess
    from pathlib import Path
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            errors="replace",
            check=True
        )
        path = Path(res.stdout.strip())
        return path.name.lower()
    except Exception:
        return None
