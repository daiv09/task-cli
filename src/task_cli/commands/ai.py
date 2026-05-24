import typer
import json
import subprocess
import difflib
import pyperclip
from pathlib import Path
from datetime import datetime

from ..app import ai_app, service, console, err_console, complete_task_id, resolve_id, get_git_repo_name
from ..models import TaskStatus, Priority
from ..ai_client import query_llm
from ..prompts import (
    AI_SUBTASKS_SYSTEM_PROMPT,
    GIT_SCAN_SYSTEM_PROMPT,
    README_GENERATE_SYSTEM_PROMPT,
    README_UPDATE_SYSTEM_PROMPT,
    CHANGELOG_SYSTEM_PROMPT
)
from ..formatters import TICK, BRANCH

def scan_project_files() -> str:
    try:
        summary_lines = []
        for p in Path(".").glob("*"):
            if p.is_dir() and p.name not in [".git", "node_modules", "venv", "env", "__pycache__", "build", "dist"]:
                summary_lines.append(f"Directory: {p.name}/")
                for sub_p in p.glob("*"):
                    if sub_p.is_file():
                        summary_lines.append(f"  - {sub_p.name}")
            elif p.is_file():
                summary_lines.append(f"File: {p.name}")
        config_files = ["pyproject.toml", "package.json", "go.mod", "Cargo.toml", "requirements.txt"]
        for cf in config_files:
            cf_path = Path(cf)
            if cf_path.exists():
                summary_lines.append(f"\n--- Content of {cf} (first 20 lines) ---")
                try:
                    lines = cf_path.read_text().splitlines()[:20]
                    summary_lines.extend(lines)
                except Exception:
                    pass
        return "\n".join(summary_lines)
    except Exception as e:
        return f"Error scanning files: {e}"

def show_unified_diff(old_text: str, new_text: str, filename: str = "README.md") -> bool:
    diff = list(difflib.unified_diff(
        old_text.splitlines(keepends=True),
        new_text.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}"
    ))
    if not diff:
        console.print("[yellow]No updates proposed by AI.[/yellow]")
        return False
    diff_text = "".join(diff)
    from rich.syntax import Syntax
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)
    return True

@ai_app.command(name="sub")
def ai_subtasks(task_id: str = typer.Argument(..., autocompletion=complete_task_id, help="ID of the task to generate subtasks for")):
    """Use AI to generate subtasks and attach them to a task"""
    task_id = resolve_id(task_id)
    task = service.get_task(task_id)
    if not task:
        err_console.print(f"[red]Error: Task {task_id} not found.[/red]")
        raise typer.Exit(code=1)
    if not task.description:
        err_console.print("[red]Error: Task description is empty.[/red]")
        raise typer.Exit(code=1)
    
    sys_prompt = AI_SUBTASKS_SYSTEM_PROMPT
    user_prompt = f"Task Description: {task.description}"
    try:
        with console.status("[bold green]Generating subtasks using AI..."):
            res = query_llm(sys_prompt, user_prompt, json_format=True)
            data = json.loads(res.strip())
            subtasks = data.get("subtasks", [])
        if not subtasks:
            console.print("[yellow]No subtasks returned by AI.[/yellow]")
            return
        service.repository.save_backup()
        for sub_desc in subtasks:
            service.add_subtask(task_id, sub_desc)
        console.print(f"[green]{TICK} Added {len(subtasks)} subtasks to task {task_id[:8]}:[/green]")
        for sub_desc in subtasks:
            console.print(f"  {BRANCH} [cyan]{sub_desc}[/cyan]")
    except Exception as e:
        console.print(f"[red]Failed to generate subtasks: {e}[/red]")

@ai_app.command(name="scan")
def git_workspace_scan():
    """Scan git repository changes and use AI to suggest new tasks"""
    repo_name = get_git_repo_name()
    if not repo_name:
        err_console.print("[red]Error: Current directory is not a Git repository.[/red]")
        raise typer.Exit(code=1)
    try:
        diff_res = subprocess.run(["git", "diff"], capture_output=True, text=True, errors="replace", check=True)
        status_res = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, errors="replace", check=True)
    except Exception as e:
        err_console.print(f"[red]Error running git commands: {e}[/red]")
        raise typer.Exit(code=1)
    diff_text = diff_res.stdout.strip()
    status_text = status_res.stdout.strip()
    if not diff_text and not status_text:
        console.print(f"[green]{TICK} No uncommitted changes or untracked files in Git workspace.[/green]")
        return
    if len(diff_text) > 4000:
        diff_text = diff_text[:4000] + "\n[Diff truncated...]"
    sys_prompt = GIT_SCAN_SYSTEM_PROMPT
    user_prompt = f"Git Status:\n{status_text}\n\nGit Diff:\n{diff_text}"
    try:
        with console.status("[bold green]Analyzing workspace changes with AI..."):
            res = query_llm(sys_prompt, user_prompt, json_format=True)
            data = json.loads(res.strip())
            tasks_list = data.get("tasks", [])
        if not tasks_list:
            console.print("[green]AI analyzed changes and found no suggestions.[/green]")
            return
        console.print(f"\n[bold cyan]AI suggested {len(tasks_list)} tasks to add:[/bold cyan]\n")
        service.repository.save_backup()
        added_count = 0
        from rich.prompt import Confirm
        for t_info in tasks_list:
            desc = t_info.get("description", "")
            pri_str = t_info.get("priority", "low")
            proj = t_info.get("project") or repo_name
            from ..models import Priority
            try:
                pri = Priority(pri_str.lower())
            except ValueError:
                pri = Priority.LOW
            confirm = Confirm.ask(f"Add task: [bold]{desc}[/bold] (Priority: [yellow]{pri.value}[/yellow], Project: [blue]{proj}[/blue])?")
            if confirm:
                service.add_task(description=desc, priority=pri, project=proj)
                console.print(f"[green]{TICK} Added.[/green]")
                added_count += 1
            else:
                console.print("[yellow]Skipped.[/yellow]")
        console.print(f"\n[green]{TICK} Successfully added {added_count} tasks to your backlog.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to run workspace scan: {e}[/red]")

@ai_app.command(name="readme")
def ai_readme():
    """Generate or propose updates to README.md using AI"""
    readme_path = Path("README.md")
    workspace_summary = scan_project_files()
    if not readme_path.exists():
        console.print("[yellow]README.md not found. Generating a new one...[/yellow]")
        sys_prompt = README_GENERATE_SYSTEM_PROMPT
        user_prompt = f"Workspace details:\n{workspace_summary}"
        try:
            with console.status("[bold green]Generating README.md using AI..."):
                generated_md = query_llm(sys_prompt, user_prompt)
            readme_path.write_text(generated_md.strip())
            console.print(f"[green]{TICK} README.md successfully created.[/green]")
        except Exception as e:
            console.print(f"[red]Failed to generate README.md: {e}[/red]")
    else:
        console.print("[cyan]README.md exists. Analyzing recently completed tasks to propose updates...[/cyan]")
        tasks = service.list_tasks(status=TaskStatus.DONE, include_waiting=True)
        if tasks:
            done_tasks_str = "\n".join(f"- {t.description} (Project: {t.project or 'None'}, Completed: {t.updated_at[:10]})" for t in tasks)
        else:
            done_tasks_str = "No tasks have been completed recently."
        sys_prompt = README_UPDATE_SYSTEM_PROMPT
        old_readme = readme_path.read_text()
        user_prompt = (
            f"Existing README.md:\n{old_readme}\n\n"
            f"Recently Completed Tasks:\n{done_tasks_str}\n\n"
            f"Workspace summary:\n{workspace_summary}"
        )
        try:
            with console.status("[bold green]Analyzing & preparing updates to README.md..."):
                new_readme = query_llm(sys_prompt, user_prompt).strip()
            if new_readme.startswith("```markdown"):
                new_readme = new_readme[11:].lstrip()
            elif new_readme.startswith("```"):
                new_readme = new_readme[3:].lstrip()
            if new_readme.endswith("```"):
                new_readme = new_readme[:-3].rstrip()
            if old_readme.strip() == new_readme.strip():
                console.print(f"[green]{TICK} README.md is already up to date.[/green]")
                return
            console.print("\n[bold cyan]Proposed changes to README.md:[/bold cyan]\n")
            has_diff = show_unified_diff(old_readme, new_readme, "README.md")
            if has_diff:
                from rich.prompt import Confirm
                confirm = Confirm.ask("Apply these updates to README.md?")
                if confirm:
                    readme_path.write_text(new_readme)
                    console.print(f"[green]{TICK} README.md updated.[/green]")
                else:
                    console.print("[yellow]Cancelled.[/yellow]")
        except Exception as e:
            console.print(f"[red]Failed to update README.md: {e}[/red]")

@ai_app.command(name="changelog")
def ai_changelog(
    days: int = typer.Option(7, "--days", "-d", help="Generate changelog for tasks completed in the last N days")
):
    """Generate a Pull Request description or Release Changelog using AI and copy to clipboard"""
    tasks = service.list_tasks(status=TaskStatus.DONE, include_waiting=True)
    recent_tasks = []
    now = datetime.now()
    for t in tasks:
        try:
            completed_dt = datetime.fromisoformat(t.updated_at)
            if (now - completed_dt).days <= days:
                recent_tasks.append(t)
        except Exception:
            recent_tasks.append(t)
    if not recent_tasks:
        console.print(f"[yellow]No tasks completed in the last {days} days.[/yellow]")
        return
    tasks_details = "\n".join(
        f"- {t.description} (Project: {t.project or 'None'}, Priority: {t.priority.value}, ID: {t.id})"
        for t in recent_tasks
    )
    sys_prompt = CHANGELOG_SYSTEM_PROMPT
    user_prompt = f"Completed tasks in the last {days} days:\n{tasks_details}"
    try:
        with console.status("[bold green]Synthesizing changelog using AI..."):
            changelog_text = query_llm(sys_prompt, user_prompt).strip()
        console.print("\n[bold cyan]Generated Release Notes / PR Description:[/bold cyan]\n")
        console.print(changelog_text)
        console.print()
        pyperclip.copy(changelog_text)
        console.print(f"[green]{TICK} Changelog copied to clipboard successfully![/green]")
    except Exception as e:
        console.print(f"[red]Failed to generate changelog: {e}[/red]")
