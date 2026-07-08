# task-cli

A fully featured, clean, and modular CLI Task Manager written in Python. Uses a custom status nomenclature (`do`, `doing`, `done`) replacing the traditional (todo, in-progress, done).

Now upgraded with robust SQLite storage, multi-level transactional undo, automated legacy data migration, and a clean modular codebase.

## Features

- **SQLite Database Backend**: Fast, transactional storage (`tasks.db`) with automatic schemas and migrations.
- **Legacy Auto-Migration**: Automatically detects and safely migrates older `tasks.json` task files to SQLite on startup.
- **3-Char Alphanumeric IDs**: Compact and easy-to-type ID space with runtime collision checks.
- **Platformdirs Support**: Clean data storage in standard, cross-platform directories (e.g. `%LOCALAPPDATA%` on Windows, `~/.local/share` on Linux/macOS).
- **Multi-Level Undo**: Fully transactional backup and state recovery system using `t undo`.
- **Power-User Aliases**: Shorthand subcommands (e.g., `t a` for add, `t ls` for list).
- **Rich Interactive Shell**: Direct, in-memory REPL shell (`t shell`) with keyboard exception handling.
- **AI-Powered Command Extensions (`tai`)**: Subtask breakdown, git workspace scans, auto-generated documentation, and changelogs.
- **Terminal Autocomplete**: Native shell autocompletion for subcommands and active task IDs.

## Installation

```bash
# Set up environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install the package
pip install -e .
```

This registers the global commands `task` and `t`.

## Usage & Advanced Features

### Creating Tasks (with metadata)
You can simply add tasks, or use advanced tags (`+work`), project (`--project`), priority (`-p`), and due dates.
```bash
# Aliases 'a' and 'add' work
t a "Review pull requests +frontend +work" -p high --project core --due 2026-03-10
t a "Pay rent" --due 2026-04-01
```

### Recurrence & Wait (Scheduling)
Auto-create new tasks when you mark a recurrent one as done. Hide tasks until a certain date.
```bash
t a "Weekly review" --due 2026-03-10 --recur weekly
t a "Renew domain" --wait 2026-06-01
```

### Listing & Filtering
The `list` command (alias `ls`) supports powerful combinations.
```bash
# List all "do" tasks
t ls do

# Filter natively
t ls --priority high
t ls --project website
t ls --before 2026-03-10
t ls --after 2026-03-01
t ls --tag work

# Sort your output
t ls --sort priority
t ls --sort created
t ls --sort due

# Show hiding tasks (Wait flag hides them by default)
t ls --all
```

### Contexts & Focus
Filter all your operations by setting a persistent context, or use focus mode.
```bash
# Only see +work tags until cleared
t context work
t context none

# Show tasks due today
t today

# Show top 5 most important
t next

# Focus on exactly one DOING task or the highest priority DO task
t focus
```

### Task Operations
All operations support 3-character task ID autocompletion via `TAB`.
```bash
t mark-doing <id>
t mark-done <id>   # (Triggers recurrence if configured)
t mark-do <id>

t update <id> "New description +newtag"
t delete <id>
```

### Transactional Undo
Reverts the last modification (adds, edits, status transitions, subtasks, deletions) instantly.
```bash
t undo
```

### Stats & Integrations
```bash
# See your current tracking stats
t stats

# Export to JSON or Markdown
t export tasks_backup.json
t export tasks_backup.md --format md

# Import from JSON
t import-tasks tasks_backup.json
```

### Shell Autocomplete Setup
Enable tab completion for task IDs and subcommands in your terminal.
To install auto-completion configuration for your shell (supports Bash, Zsh, Fish, or PowerShell), run:
```bash
# Register completion for 't'
t --install-completion

# Register completion for 'task'
task --install-completion
```
*Note: Restart your terminal session after running this command. You will then be able to press `TAB` to auto-complete task IDs for commands like `update`, `mark-done`, `start`, `sub`, etc.*

### AI Assistant & Agentic Features (tai)
The `tai` subcommands leverage AI models (via OpenAI-compatible endpoints) to bring intelligence directly to your workspace backlog. Make sure your `.env` contains your `AI_API_KEY`, `AI_BASE_URL`, and `AI_MODEL` configured.

```bash
# Break down an existing task into 3-5 subtasks using AI
tai sub <id>

# Scan your git repository status and diffs to interactively propose backlog tasks
tai scan

# Analyze completed tasks and workspace files to propose documentation updates to README.md
tai readme

# Generate release notes or PR description for tasks completed in the last N days (copied to clipboard)
tai changelog --days 7

# Run any terminal command. If it fails, AI analyzes the stderr logs and automatically registers a high-priority bug task (+bug) to your backlog!
t run "npm test"
```

### File Locations & Configuration
- **Database Path**: Stored cross-platform via `platformdirs`.
  - Windows: `%LOCALAPPDATA%\task-cli\tasks.db`
  - macOS: `~/Library/Application Support/task-cli/tasks.db`
  - Linux: `~/.local/share/task-cli/tasks.db`
- **Config**: You can create `~/.task-cli.toml` with:
```toml
[task-cli]
default_project = "core"
```
- **Hooks**: Place executable scripts in `~/.task-cli/hooks/on-add`, `on-update`, and `on-done` for custom event scripting.

### Testing
The project uses `pytest` for testing. You can run the test suite using:
```bash
pytest
```

### Dependencies
The project uses the following dependencies:
- `typer`: CLI framework
- `rich`: Formatting and tables
- `platformdirs`: Clean directory resolution
- `tomli`: TOML configuration parsing
- `pyperclip`: Clipboard integration
- `httpx`: AI LLM requests
- `python-dotenv`: Environment configuration
