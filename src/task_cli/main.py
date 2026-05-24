import typer
from typing import Optional
from pathlib import Path

# Import shared app state and helper functions
from .app import app, ai_app, console, get_git_repo_name
from .config import VERSION, settings

# Import command modules to register all Typer commands
from .commands import core
from .commands import ai

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

    # Smart Auto-Contexting
    import os
    import sys
    if os.environ.get("TASK_DB_PATH") or "pytest" in sys.modules:
        settings.auto_context = None
    else:
        git_repo = get_git_repo_name()
        if git_repo:
            settings.auto_context = git_repo
        else:
            try:
                extensions = {}
                for p in Path(".").glob("*"):
                    if p.is_file():
                        ext = p.suffix.lower()
                        if ext in [".py", ".js", ".ts", ".rs", ".go", ".cpp", ".java"]:
                            extensions[ext] = extensions.get(ext, 0) + 1
                if extensions:
                    best_ext = max(extensions, key=extensions.get)
                    mapping = {
                        ".py": "python",
                        ".js": "javascript",
                        ".ts": "typescript",
                        ".rs": "rust",
                        ".go": "go",
                        ".cpp": "cpp",
                        ".java": "java"
                    }
                    settings.auto_context = mapping.get(best_ext)
            except Exception:
                pass

if __name__ == "__main__":
    app()
