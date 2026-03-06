# Task CLI (Power-User Edition)

A fully featured but clean CLI Task Manager written in Python. Uses a custom status nomenclature (`do`, `doing`, `done`) replacing the traditional (todo, in-progress, done). 

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

This registers the commands `task` and `t`.

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
```bash
t mark-doing <id>
t mark-done <id>   # (Triggers recurrence if configured)
t mark-do <id>

t update <id> "New description +newtag"
t delete <id>
```

### Stats & Integrations
```bash
# See your current tracking stats
t stats

# Export to JSON or Markdown
t export tasks_backup.json
t export tasks_backup.md --format md

# Import from JSON
t import tasks_backup.json
```

### Hooks & Configuration
- **Hooks**: You can place executables in `~/.task-cli/hooks/on-add`, `on-update`, and `on-done`. When these actions occur, the script is called with a `TASK_JSON` environment variable containing the task data.
- **Config**: You can create `~/.task-cli.toml` with:
```toml
[task-cli]
data_path = "/absolute/path/to/tasks.json"
default_project = "none"
```

