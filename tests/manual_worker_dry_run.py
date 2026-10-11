
import gc
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from instagram_agent import worker
from instagram_agent.sqlite_ledger import SQLiteExecutionLedger


def main():
    with tempfile.TemporaryDirectory(
        prefix="jammer_worker_test_"
    ) as temp:
        temp_path = Path(temp)
        schedule_file = temp_path / "schedule.json"
        ledger_file = temp_path / "ledger.db"
        log_dir = temp_path / "logs"

        digest = "a" * 64

        schedule = [
            {
                "sha256": digest,
                "content_type": "post",
                "scheduled_for": "2026-10-11T10:00:00+05:30",
                "status": "scheduled",
            }
        ]

        schedule_file.write_text(
            json.dumps(schedule, indent=2),
            encoding="utf-8",
        )

        ledger = SQLiteExecutionLedger(ledger_file)

        # Redirect worker file access to temporary test data.
        worker.SCHEDULE_FILE = schedule_file
        worker.LOG_DIR = log_dir
        worker.LOG_FILE = log_dir / "worker.log"
        worker.SQLiteExecutionLedger = lambda: ledger
        worker.DRY_RUN = True

        now = datetime(
            2026,
            10,
            11,
            10,
            30,
            tzinfo=ZoneInfo("Asia/Kolkata"),
        )

        original_schedule = schedule_file.read_text(
            encoding="utf-8"
        )

        try:
            due = worker.process_due_items(now)

            assert len(due) == 1, (
                f"Expected one due item, got {len(due)}"
            )
            assert due[0]["sha256"] == digest
            assert ledger.get(digest) is None

            assert (
                schedule_file.read_text(encoding="utf-8")
                == original_schedule
            )

            print("\nPASS: Due post detected.")
            print("PASS: SQLite ledger remains unclaimed.")
            print("PASS: Schedule remains unchanged.")
            print("PASS: Test used temporary files only.")

        finally:
            # Flush and close the worker's file logging handlers.
            logging.shutdown()

            # Close any SQLite connections that remain referenced.
            del ledger
            gc.collect()


if __name__ == "__main__":
    main()
