# Task CLI (Power-User Edition) Cheatsheet

A quick reference guide for your Typer-based task manager.
> **Note**: Uses `do`, `doing`, and `done` statuses.

## 📝 Creating Tasks (Add / `a`)
```bash
# Basic task creation (status defaults to `do`)
t a "Review pull requests"

# With rich metadata (+tags natively extracted)
t a "Fix login +backend +bug" -p high --project core

# With scheduling (Due dates and Recurrence)
t a "Pay rent" --due 2026-04-01 --recur monthly
t a "Renew domain" --wait 2026-06-01  # Hides task until date

# Quick add (instant high-priority task)
t quick "Server is down"

# Create task from clipboard text
t clip

# Add a subtask to an existing task
t sub <id> "Write tests"
```

## 📋 Listing & Filtering (List / `ls`)
```bash
# Basic lists by status
t ls         # Shows DO and DOING
t ls do      # Shows only DO tasks
t ls doing   # Shows only DOING tasks
t ls done    # Shows only DONE tasks

# Advanced filtering
t ls --priority high
t ls --tag backend
t ls --project core
t ls --before 2026-03-10
t ls --after 2026-03-01

# Sorting outputs
t ls --sort priority  # Or: due, created

# Overdue & Hidden
t ls --overdue   # Tasks past their due date
t ls --all       # Includes tasks hidden by `--wait`

# Search by keyword
t search "database"
```

## 🎯 Focus & Productivity Views
```bash
# Show tasks due today or overdue
t today

# Show the 5 most important tasks (weighted by priority & due)
t next

# Show a single current 'doing' task for pure focus
t focus

# Lock your CLI context to a specific tag (affects all future `ls` commands)
t context work
t context none   # Clears context

# Display high-level dashboard
t dashboard
```

## ⏱️ Time Tracking
```bash
# Start tracking time for a task (or create & start)
t start <id>
t start "New task description"

# Stop time tracking
t stop
t stop <id>
```

## 🔄 Manipulating Tasks
```bash
# Change Status
t mark-doing <id>
t mark-done <id>  # (Will auto-generate next task if recur is set)
t mark-do <id>

# Modify Description (re-extracts tags)
t update <id> "New description +newtag"

# Delete or Clear
t delete <id>
t clear           # Deletes ALL tasks

# Undo last destructive operation
t undo
```

## 🖥️ Interactive Mode
```bash
# Start interactive task shell
t shell
```

## 📊 Data, Config & Sync
```bash
# View summary statistics
t stats

# Archive completed tasks
t archive

# Export & Import
t export backup.json
t export backup.md --format md
t import-tasks backup.json
```

**Configuration Path**: `~/.task-cli.toml`
**Background Hooks Path**: `~/.task-cli/hooks/on-add`, `on-update`, `on-done`
