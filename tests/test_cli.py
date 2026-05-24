import os
import tempfile

# Force a isolated temp database for all pytest runs
TEST_DB_FILE = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
TEST_DB_FILE.close()
os.environ["TASK_DB_PATH"] = TEST_DB_FILE.name

import pytest
from typer.testing import CliRunner
from task_cli.main import app
from task_cli.config import DEFAULT_FILE_PATH

runner = CliRunner()

@pytest.fixture(autouse=True)
def isolated_db():
    from pathlib import Path
    from task_cli.config import settings
    settings.auto_context = None
    history_file = Path.home() / ".task-cli" / "history.jsonl"
    db_file = DEFAULT_FILE_PATH.with_suffix(".db")
    for f in [DEFAULT_FILE_PATH, db_file, history_file]:
        if f.exists():
            f.unlink()
    yield
    for f in [DEFAULT_FILE_PATH, db_file, history_file]:
        if f.exists():
            f.unlink()

def test_add_task():
    result = runner.invoke(app, ["add", "Buy groceries"])
    assert result.exit_code == 0
    assert "Created task " in result.stdout

def test_list_tasks():
    runner.invoke(app, ["add", "Test task 1"])
    runner.invoke(app, ["add", "Test task 2"])
    
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Test task 1" in result.stdout
    assert "Test task 2" in result.stdout

def test_mark_done():
    # Add a task
    add_result = runner.invoke(app, ["add", "To be completed"])
    # "Created task 66718ba3 (do)"
    task_id = add_result.stdout.split("Created task ")[1].split(" ")[0].strip()

    # Mark done
    result = runner.invoke(app, ["mark-done", task_id])
    assert result.exit_code == 0
    assert f"now done" in result.stdout

    # Verify list done
    list_done_result = runner.invoke(app, ["list", "done"])
    assert list_done_result.exit_code == 0
    assert "To be completed" in list_done_result.stdout

def test_alphanumeric_id_generation():
    add_result = runner.invoke(app, ["add", "Test task for ID check"])
    assert add_result.exit_code == 0
    task_id = add_result.stdout.split("Created task ")[1].split(" ")[0].strip()
    assert len(task_id) == 3
    assert task_id.isalnum()

def test_date_standardization():
    add_result_nlp = runner.invoke(app, ["add", "Test task due today"])
    assert add_result_nlp.exit_code == 0
    
    from task_cli.service import TaskService
    service = TaskService()
    tasks = service.list_tasks()
    found = False
    for t in tasks:
        if "Test task due" in t.description or "today" in t.description:
            assert t.due.endswith("T23:59:59")
            found = True
    assert found

def test_id_collision_avoidance(monkeypatch):
    import random
    calls = []
    
    add_res1 = runner.invoke(app, ["add", "Task 1"])
    task_id1 = add_res1.stdout.split("Created task ")[1].split(" ")[0].strip()
    
    def mock_choices(population, k=3):
        calls.append(1)
        if len(calls) == 1:
            return list(task_id1)
        else:
            return ['x', 'y', 'z']
            
    monkeypatch.setattr(random, "choices", mock_choices)
    
    add_res2 = runner.invoke(app, ["add", "Task 2"])
    assert add_res2.exit_code == 0
    task_id2 = add_res2.stdout.split("Created task ")[1].split(" ")[0].strip()
    
    assert task_id2 == "xyz"
    assert len(calls) == 2

def test_corrupted_db_exits():
    DEFAULT_FILE_PATH.write_text("{invalid json}")
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
    assert "corrupted" in result.stdout or "corrupted" in result.stderr

def test_multi_level_undo():
    res_a = runner.invoke(app, ["add", "Task A"])
    id_a = res_a.stdout.split("Created task ")[1].split(" ")[0].strip()

    res_b = runner.invoke(app, ["add", "Task B"])
    id_b = res_b.stdout.split("Created task ")[1].split(" ")[0].strip()

    res_c = runner.invoke(app, ["add", "Task C"])
    id_c = res_c.stdout.split("Created task ")[1].split(" ")[0].strip()

    list_res = runner.invoke(app, ["list"])
    assert "Task A" in list_res.stdout
    assert "Task B" in list_res.stdout
    assert "Task C" in list_res.stdout

    undo_res = runner.invoke(app, ["undo"])
    assert undo_res.exit_code == 0
    
    list_res = runner.invoke(app, ["list"])
    assert "Task A" in list_res.stdout
    assert "Task B" in list_res.stdout
    assert "Task C" not in list_res.stdout

    undo_res = runner.invoke(app, ["undo"])
    assert undo_res.exit_code == 0
    
    list_res = runner.invoke(app, ["list"])
    assert "Task A" in list_res.stdout
    assert "Task B" not in list_res.stdout
    assert "Task C" not in list_res.stdout

def test_sqlite_migration():
    import json
    task_data = [{
        "id": "migr01",
        "description": "Migrated task",
        "status": "do",
        "priority": "high",
        "tags": ["test", "migration"],
        "project": "migration_proj",
        "due": None,
        "recur": None,
        "wait": None,
        "subtasks": ["sub1"],
        "start_time": None,
        "total_duration": 0,
        "created_at": "2026-05-24T12:00:00",
        "updated_at": "2026-05-24T12:00:00"
    }]
    DEFAULT_FILE_PATH.write_text(json.dumps(task_data), encoding="utf-8")
    
    list_res = runner.invoke(app, ["list"])
    assert list_res.exit_code == 0
    assert "Migrated task" in list_res.stdout
    
    assert not DEFAULT_FILE_PATH.exists()
    assert DEFAULT_FILE_PATH.with_suffix(".db").exists()


