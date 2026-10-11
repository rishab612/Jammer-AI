
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEDGER_FILE = (
    PROJECT_ROOT
    / "instagram_agent"
    / "queue"
    / "execution_ledger.json"
)

VALID_STATES = {
    "pending",
    "claimed",
    "published",
    "failed",
    "uncertain",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ExecutionLedger:
    """Persistent local record of scheduled execution attempts."""

    def __init__(self, ledger_file=LEDGER_FILE):
        self.ledger_file = Path(ledger_file)
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.ledger_file.exists():
            self._save([])

    def _load(self):
        try:
            with self.ledger_file.open("r", encoding="utf-8") as file:
                records = json.load(file)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Execution ledger JSON is invalid. Preserve and repair "
                "the file before continuing."
            ) from error

        if not isinstance(records, list):
            raise RuntimeError("Execution ledger must be a JSON list.")

        seen = set()

        for record in records:
            if not isinstance(record, dict):
                raise RuntimeError("Execution ledger contains an invalid record.")

            key = record.get("sha256")
            state = record.get("state")

            if not isinstance(key, str) or not key:
                raise RuntimeError("Execution ledger record has no sha256.")

            if key in seen:
                raise RuntimeError(f"Duplicate ledger record: {key}")

            if state not in VALID_STATES:
                raise RuntimeError(f"Invalid ledger state: {state!r}")

            seen.add(key)

        return records

    def _save(self, records):
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.ledger_file.with_suffix(".tmp")

        with temporary.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=2, ensure_ascii=False)
            file.flush()

        temporary.replace(self.ledger_file)

    def get(self, sha256):
        for record in self._load():
            if record["sha256"] == sha256:
                return record
        return None

    def claim(self, sha256):
        """Claim a new item. Existing records are never silently reset."""
        if not isinstance(sha256, str) or not sha256.strip():
            raise ValueError("sha256 must be a non-empty string.")

        records = self._load()

        for record in records:
            if record["sha256"] == sha256:
                raise ValueError(
                    f"Item already recorded with state {record['state']!r}; "
                    "manual inspection is required."
                )

        record = {
            "sha256": sha256,
            "state": "claimed",
            "claimed_at": utc_now(),
            "completed_at": None,
            "instagram_media_id": None,
            "last_error": None,
        }

        records.append(record)
        self._save(records)
        return record

    def mark_published(self, sha256, instagram_media_id):
        if not isinstance(instagram_media_id, str) or not instagram_media_id.strip():
            raise ValueError("A valid Instagram media ID is required.")

        return self._transition(
            sha256,
            expected="claimed",
            new_state="published",
            instagram_media_id=instagram_media_id.strip(),
        )

    def mark_failed(self, sha256, error):
        return self._transition(
            sha256,
            expected="claimed",
            new_state="failed",
            last_error=str(error),
        )

    def mark_uncertain(self, sha256, error):
        return self._transition(
            sha256,
            expected="claimed",
            new_state="uncertain",
            last_error=str(error),
        )

    def _transition(self, sha256, expected, new_state, **updates):
        records = self._load()

        for record in records:
            if record["sha256"] == sha256:
                if record["state"] != expected:
                    raise ValueError(
                        f"Cannot change {record['state']!r} to {new_state!r}; "
                        f"expected {expected!r}."
                    )

                record.update(updates)
                record["state"] = new_state
                record["completed_at"] = utc_now()
                self._save(records)
                return record

        raise KeyError(f"Ledger record not found: {sha256}")
