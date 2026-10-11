
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from instagram_agent.execution_coordinator import ExecutionCoordinator
from instagram_agent.scheduler import (
    SCHEDULE_FILE,
    TIMEZONE_NAME,
    load_json_list,
)
from instagram_agent.sqlite_ledger import SQLiteExecutionLedger


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "instagram_agent" / "logs"
LOG_FILE = LOG_DIR / "worker.log"

# Live publishing is deliberately disabled.
DRY_RUN = True

DUE_STATUSES = {"scheduled"}


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def find_due_items(now=None):
    """Return scheduled items whose execution time has arrived."""
    zone = ZoneInfo(TIMEZONE_NAME)
    now = now or datetime.now(zone)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware.")

    now = now.astimezone(zone)
    due = []

    for item in load_json_list(SCHEDULE_FILE):
        if item.get("status") not in DUE_STATUSES:
            continue

        scheduled_text = item.get("scheduled_for")

        if not scheduled_text:
            continue

        try:
            scheduled = datetime.fromisoformat(scheduled_text)
        except (TypeError, ValueError):
            logging.error(
                "Invalid schedule timestamp: %r",
                scheduled_text,
            )
            continue

        if scheduled.tzinfo is None or scheduled.utcoffset() is None:
            logging.error(
                "Schedule timestamp has no timezone: %r",
                scheduled_text,
            )
            continue

        if scheduled.astimezone(zone) <= now:
            due.append(item)

    return due


def process_due_items(now=None, coordinator=None):
    """
    Inspect due items without publishing or claiming media.

    DRY_RUN must remain enabled until a separately tested live
    execution workflow has been implemented.
    """
    configure_logging()

    if not DRY_RUN:
        raise RuntimeError(
            "Live execution is not implemented. Keep DRY_RUN enabled."
        )

    due = find_due_items(now)

    if not due:
        logging.info("No due scheduled items.")
        return []

    # Injecting a coordinator makes the worker easy to test.
    # The default coordinator uses the SQLite execution ledger.
    if coordinator is None:
        coordinator = ExecutionCoordinator(
            ledger=SQLiteExecutionLedger()
        )

    for item in due:
        content_type = item.get("content_type", "unknown")
        digest = item.get("sha256")

        if content_type != "post":
            logging.warning(
                "Skipping %s item %s: publisher workflow is not enabled.",
                content_type,
                digest or "unknown",
            )
            continue

        if not isinstance(digest, str) or not digest.strip():
            logging.error(
                "Skipping post with missing or invalid SHA-256."
            )
            continue

        # Read-only inspection. Never create a claim during dry run.
        existing = coordinator.inspect(digest)

        if existing:
            logging.warning(
                "Skipping post %s: ledger already records state %s. "
                "No automatic retry.",
                digest,
                existing["state"],
            )
            continue

        logging.info(
            "DRY RUN: feed post %s is due and has no ledger record. "
            "No claim was created and nothing was published.",
            digest,
        )

    return due


def main():
    print("Jammer AI Background Worker", flush=True)
    print("Mode: DRY RUN - no Instagram requests.", flush=True)
    process_due_items()


if __name__ == "__main__":
    main()
