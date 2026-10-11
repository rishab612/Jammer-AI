
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from instagram_agent import worker
from instagram_agent.sqlite_ledger import SQLiteExecutionLedger


def test_worker_dry_run_does_not_claim_media(tmp_path, monkeypatch):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")

    due_item = {
        "content_type": "post",
        "sha256": "a" * 64,
        "status": "scheduled",
        "scheduled_for": "2026-10-11T09:00:00+05:30",
    }

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "find_due_items", lambda now=None: [due_item])
    monkeypatch.setattr(worker, "DRY_RUN", True)

    worker.process_due_items(
        datetime(2026, 10, 11, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    )

    assert ledger.get("a" * 64) is None


def test_live_execution_remains_blocked(monkeypatch):
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "DRY_RUN", False)

    with pytest.raises(RuntimeError, match="Live execution is not implemented"):
        worker.process_due_items()


def test_sqlite_ledger_rejects_duplicate_media(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    digest = "b" * 64

    ledger.claim(digest)

    with pytest.raises(ValueError, match="already has an execution record"):
        ledger.claim(digest)

    assert ledger.get(digest)["state"] == "claimed"


def test_worker_skips_media_already_in_ledger(tmp_path, monkeypatch):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    digest = "c" * 64
    ledger.claim(digest)

    due_item = {
        "content_type": "post",
        "sha256": digest,
        "status": "scheduled",
        "scheduled_for": "2026-10-11T09:00:00+05:30",
    }

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "find_due_items", lambda now=None: [due_item])
    monkeypatch.setattr(worker, "SQLiteExecutionLedger", lambda: ledger)
    monkeypatch.setattr(worker, "DRY_RUN", True)

    before = ledger.get(digest)

    worker.process_due_items(
        datetime(2026, 10, 11, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    )

    after = ledger.get(digest)
    assert after == before
    assert after["state"] == "claimed"


def test_worker_dry_run_does_not_send_instagram_requests(
    tmp_path, monkeypatch
):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")

    due_item = {
        "content_type": "post",
        "sha256": "d" * 64,
        "status": "scheduled",
        "scheduled_for": "2026-10-11T09:00:00+05:30",
    }

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "find_due_items", lambda now=None: [due_item])
    monkeypatch.setattr(worker, "SQLiteExecutionLedger", lambda: ledger)
    monkeypatch.setattr(worker, "DRY_RUN", True)

    # Any attempted HTTP request should fail this test.
    import requests

    def unexpected_request(*args, **kwargs):
        pytest.fail("Dry-run worker attempted an HTTP request")

    monkeypatch.setattr(requests, "request", unexpected_request)
    monkeypatch.setattr(requests, "post", unexpected_request)

    worker.process_due_items(
        datetime(2026, 10, 11, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    )

    assert ledger.get("d" * 64) is None


def test_worker_skips_published_media(tmp_path, monkeypatch):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    digest = "e" * 64
    ledger.claim(digest)
    ledger.mark_published(digest, "test-media-id")

    due_item = {
        "content_type": "post",
        "sha256": digest,
        "status": "scheduled",
        "scheduled_for": "2026-10-11T09:00:00+05:30",
    }

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "find_due_items", lambda now=None: [due_item])
    monkeypatch.setattr(worker, "SQLiteExecutionLedger", lambda: ledger)
    monkeypatch.setattr(worker, "DRY_RUN", True)

    before = ledger.get(digest)

    worker.process_due_items(
        datetime(2026, 10, 11, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    )

    assert ledger.get(digest) == before
    assert ledger.get(digest)["state"] == "published"
    assert ledger.get(digest)["instagram_media_id"] == "test-media-id"


def test_worker_skips_non_post_without_claiming(tmp_path, monkeypatch):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")

    due_item = {
        "content_type": "story",
        "sha256": "f" * 64,
        "status": "scheduled",
        "scheduled_for": "2026-10-11T09:00:00+05:30",
    }

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "find_due_items", lambda now=None: [due_item])
    monkeypatch.setattr(worker, "SQLiteExecutionLedger", lambda: ledger)
    monkeypatch.setattr(worker, "DRY_RUN", True)

    worker.process_due_items(
        datetime(2026, 10, 11, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    )

    assert ledger.get("f" * 64) is None


def test_due_post_with_isolated_schedule_and_sqlite_ledger(
    tmp_path, monkeypatch
):
    import json

    schedule_file = tmp_path / "schedule.json"
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    digest = "9" * 64

    schedule_file.write_text(
        json.dumps([{
            "sha256": digest,
            "content_type": "post",
            "scheduled_for": "2026-10-11T10:00:00+05:30",
            "status": "scheduled",
        }]),
        encoding="utf-8",
    )

    ledger.claim(digest)
    original_record = ledger.get(digest)
    original_schedule = schedule_file.read_text(encoding="utf-8")

    monkeypatch.setattr(worker, "SCHEDULE_FILE", schedule_file)
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "SQLiteExecutionLedger", lambda: ledger)
    monkeypatch.setattr(worker, "DRY_RUN", True)

    now = datetime(
        2026, 10, 11, 10, 30,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    due = worker.process_due_items(now)

    assert len(due) == 1
    assert due[0]["sha256"] == digest
    assert ledger.get(digest) == original_record
    assert schedule_file.read_text(encoding="utf-8") == original_schedule
