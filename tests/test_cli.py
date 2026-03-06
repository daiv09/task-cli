import pytest
import os
from typer.testing import CliRunner
from task_cli.main import app
from task_cli.config import DEFAULT_FILE_PATH

runner = CliRunner()

@pytest.fixture(autouse=True)
def isolated_db():
    # Use a temporary file for testing
    old_path = os.getenv("TASK_DB_PATH")
    try:
        if DEFAULT_FILE_PATH.exists():
            DEFAULT_FILE_PATH.unlink()
        yield
    finally:
        if DEFAULT_FILE_PATH.exists():
            DEFAULT_FILE_PATH.unlink()

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
