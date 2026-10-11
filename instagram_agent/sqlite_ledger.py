
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_FILE = (
    PROJECT_ROOT
    / "instagram_agent"
    / "queue"
    / "execution_ledger.db"
)

VALID_STATES = {
    "claimed",
    "published",
    "failed",
    "uncertain",
}

RECOVERABLE_STATES = {"claimed", "uncertain"}


def utc_now():
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class SQLiteExecutionLedger:
    """Transactional execution ledger with audited recovery."""

    def __init__(self, database_file=DATABASE_FILE):
        self.database_file = Path(database_file)
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            self.database_file,
            timeout=10,
            isolation_level="IMMEDIATE",
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self):
        """Create tables without deleting existing ledger records."""
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    sha256 TEXT PRIMARY KEY,
                    state TEXT NOT NULL
                        CHECK (state IN (
                            'claimed', 'published', 'failed', 'uncertain'
                        )),
                    claimed_at TEXT NOT NULL,
                    completed_at TEXT,
                    instagram_media_id TEXT,
                    last_error TEXT
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS recovery_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sha256 TEXT NOT NULL,
                    prior_state TEXT NOT NULL,
                    resolution TEXT NOT NULL,
                    operator TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    resolved_at TEXT NOT NULL
                )
            """)

    def get(self, sha256):
        """Return an execution record or None."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM executions WHERE sha256 = ?",
                (sha256,),
            ).fetchone()

        return dict(row) if row else None

    def list_by_states(self, states=None):
        """List execution records, optionally filtered by state."""
        if states is None:
            states = RECOVERABLE_STATES

        states = set(states)

        if not states:
            return []

        invalid_states = states - VALID_STATES
        if invalid_states:
            raise ValueError(
                f"Invalid execution states: {sorted(invalid_states)}"
            )

        placeholders = ", ".join("?" for _ in states)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM executions
                WHERE state IN ({placeholders})
                ORDER BY claimed_at ASC
                """,
                tuple(sorted(states)),
            ).fetchall()

        return [dict(row) for row in rows]

    def claim(self, sha256):
        """
        Atomically reserve a media hash.

        Existing records are never reclaimed automatically, regardless
        of their state.
        """
        if not isinstance(sha256, str) or not sha256.strip():
            raise ValueError("sha256 must be a non-empty string.")

        sha256 = sha256.strip()

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO executions
                        (sha256, state, claimed_at)
                    VALUES (?, 'claimed', ?)
                    """,
                    (sha256, utc_now()),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                f"Media already has an execution record: {sha256}. "
                "Inspect its state; do not automatically retry."
            ) from error

        return self.get(sha256)

    def _transition(self, sha256, expected, new_state, **updates):
        """Perform a state transition only from the expected state."""
        allowed_columns = {
            "completed_at",
            "instagram_media_id",
            "last_error",
        }

        if set(updates) - allowed_columns:
            raise ValueError("Unsupported ledger field.")

        assignments = ["state = ?"]
        values = [new_state]

        for column, value in updates.items():
            assignments.append(f"{column} = ?")
            values.append(value)

        values.extend([sha256, expected])

        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE executions
                SET {", ".join(assignments)}
                WHERE sha256 = ? AND state = ?
                """,
                values,
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Transition to {new_state!r} rejected: "
                    "record missing or current state is not "
                    f"{expected!r}."
                )

        return self.get(sha256)

    def mark_published(self, sha256, instagram_media_id):
        """Record a confirmed Instagram media ID."""
        if (
            not isinstance(instagram_media_id, str)
            or not instagram_media_id.strip()
        ):
            raise ValueError("A valid Instagram media ID is required.")

        return self._transition(
            sha256,
            "claimed",
            "published",
            completed_at=utc_now(),
            instagram_media_id=instagram_media_id.strip(),
        )

    def mark_failed(self, sha256, error):
        """Record a failed execution without enabling a retry."""
        return self._transition(
            sha256,
            "claimed",
            "failed",
            completed_at=utc_now(),
            last_error=str(error),
        )

    def mark_uncertain(self, sha256, error):
        """Record an execution whose external outcome is unknown."""
        return self._transition(
            sha256,
            "claimed",
            "uncertain",
            completed_at=utc_now(),
            last_error=str(error),
        )

    def resolve_not_published(self, sha256, *, operator, reason):
        """
        Manually resolve a claimed or uncertain execution as not published.

        The state update and audit entry are committed in one transaction.
        This method does not contact Instagram, publish media, or retry it.
        The media hash remains reserved in the executions table.
        """
        if not isinstance(sha256, str) or not sha256.strip():
            raise ValueError("sha256 must be a non-empty string.")

        if not isinstance(operator, str) or not operator.strip():
            raise ValueError("A non-empty operator identity is required.")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A non-empty recovery reason is required.")

        sha256 = sha256.strip()
        operator = operator.strip()
        reason = reason.strip()
        resolved_at = utc_now()

        with self._connect() as connection:
            record = connection.execute(
                """
                SELECT state
                FROM executions
                WHERE sha256 = ?
                """,
                (sha256,),
            ).fetchone()

            if record is None:
                raise ValueError(
                    f"Cannot resolve missing execution: {sha256}"
                )

            prior_state = record["state"]

            if prior_state not in RECOVERABLE_STATES:
                raise ValueError(
                    "Recovery resolution rejected: expected state "
                    f"'claimed' or 'uncertain', got {prior_state!r}."
                )

            cursor = connection.execute(
                """
                UPDATE executions
                SET state = 'failed',
                    completed_at = ?,
                    last_error = ?
                WHERE sha256 = ? AND state = ?
                """,
                (
                    resolved_at,
                    f"Manually resolved as not published: {reason}",
                    sha256,
                    prior_state,
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    "Recovery resolution rejected because the state changed."
                )

            connection.execute(
                """
                INSERT INTO recovery_audit (
                    sha256,
                    prior_state,
                    resolution,
                    operator,
                    reason,
                    resolved_at
                )
                VALUES (?, ?, 'not_published', ?, ?, ?)
                """,
                (
                    sha256,
                    prior_state,
                    operator,
                    reason,
                    resolved_at,
                ),
            )

        return self.get(sha256)

    def list_recovery_audit(self, sha256=None):
        """Read recovery audit records without modifying the ledger."""
        with self._connect() as connection:
            if sha256 is None:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM recovery_audit
                    ORDER BY id ASC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM recovery_audit
                    WHERE sha256 = ?
                    ORDER BY id ASC
                    """,
                    (sha256,),
                ).fetchall()

        return [dict(row) for row in rows]
