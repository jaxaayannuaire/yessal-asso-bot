from datetime import time
from unittest.mock import MagicMock

from modules.scheduler import configure_scheduled_jobs


def test_configure_scheduled_jobs_registers_expected_jobs():
    app = MagicMock()
    queue = app.job_queue

    configured = configure_scheduled_jobs(app)

    assert configured is True
    assert queue.run_repeating.call_count == 4
    assert queue.run_daily.call_count == 1

    intervals = [call.kwargs["interval"] for call in queue.run_repeating.call_args_list]
    assert 15 * 60 in intervals
    assert 30 * 60 in intervals
    assert 60 * 60 in intervals
    assert 7 * 24 * 60 * 60 in intervals


def test_configure_scheduled_jobs_backup_is_at_six():
    app = MagicMock()
    queue = app.job_queue

    configure_scheduled_jobs(app)

    backup_call = queue.run_daily.call_args
    assert backup_call.kwargs["name"] == "backup_duckdb_daily"
    assert backup_call.kwargs["time"].hour == 6
    assert backup_call.kwargs["time"].minute == 0


def test_configure_scheduled_jobs_returns_false_without_queue():
    app = MagicMock()
    app.job_queue = None

    assert configure_scheduled_jobs(app) is False
