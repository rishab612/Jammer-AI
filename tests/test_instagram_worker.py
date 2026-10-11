
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from instagram_agent import worker


def test_finds_due_post(tmp_path, monkeypatch):
    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(json.dumps([{
        "sha256": "due-post",
        "content_type": "post",
        "scheduled_for": "2026-10-11T10:00:00+05:30",
        "status": "scheduled",
    }]), encoding="utf-8")

    monkeypatch.setattr(worker, "SCHEDULE_FILE", schedule_file)

    now = datetime(
        2026, 10, 11, 10, 30,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    due = worker.find_due_items(now)

    assert len(due) == 1
    assert due[0]["sha256"] == "due-post"


def test_ignores_future_post(tmp_path, monkeypatch):
    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(json.dumps([{
        "sha256": "future-post",
        "content_type": "post",
        "scheduled_for": "2026-10-12T10:00:00+05:30",
        "status": "scheduled",
    }]), encoding="utf-8")

    monkeypatch.setattr(worker, "SCHEDULE_FILE", schedule_file)

    now = datetime(
        2026, 10, 11, 10, 30,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    assert worker.find_due_items(now) == []


def test_ignores_non_scheduled_items(tmp_path, monkeypatch):
    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(json.dumps([{
        "sha256": "already-published",
        "content_type": "post",
        "scheduled_for": "2026-10-10T10:00:00+05:30",
        "status": "published",
    }]), encoding="utf-8")

    monkeypatch.setattr(worker, "SCHEDULE_FILE", schedule_file)

    now = datetime(
        2026, 10, 11, 10, 30,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    assert worker.find_due_items(now) == []


def test_rejects_naive_now():
    with pytest.raises(ValueError):
        worker.find_due_items(datetime(2026, 10, 11, 10, 30))


def test_dry_run_does_not_change_schedule(tmp_path, monkeypatch):
    schedule_file = tmp_path / "schedule.json"
    original = [{
        "sha256": "due-post",
        "content_type": "post",
        "scheduled_for": "2026-10-11T10:00:00+05:30",
        "status": "scheduled",
    }]
    original_text = json.dumps(original)
    schedule_file.write_text(original_text, encoding="utf-8")

    monkeypatch.setattr(worker, "SCHEDULE_FILE", schedule_file)
    monkeypatch.setattr(worker, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(worker, "LOG_FILE", tmp_path / "logs" / "worker.log")

    now = datetime(
        2026, 10, 11, 10, 30,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    due = worker.process_due_items(now)

    assert len(due) == 1
    assert schedule_file.read_text(encoding="utf-8") == original_text


def test_live_execution_is_blocked(monkeypatch):
    monkeypatch.setattr(worker, "DRY_RUN", False)

    with pytest.raises(RuntimeError, match="Live execution is not implemented"):
        worker.process_due_items()


def test_dry_run_does_not_claim_execution(tmp_path, monkeypatch):
    from instagram_agent.execution_ledger import ExecutionLedger

    schedule_file = tmp_path / "schedule.json"
    schedule_file.write_text(json.dumps([{
        "sha256": "dry-run-hash",
        "content_type": "post",
        "scheduled_for": "2026-10-11T10:00:00+05:30",
        "status": "scheduled",
    }]), encoding="utf-8")

    ledger_file = tmp_path / "execution_ledger.json"

    monkeypatch.setattr(worker, "SCHEDULE_FILE", schedule_file)
    monkeypatch.setattr(worker, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(worker, "LOG_FILE", tmp_path / "logs" / "worker.log")

    now = datetime(
        2026, 10, 11, 10, 30,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    due = worker.process_due_items(now)

    ledger = ExecutionLedger(ledger_file)

    assert len(due) == 1
    assert ledger.get("dry-run-hash") is None
