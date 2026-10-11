
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from instagram_agent.sqlite_ledger import SQLiteExecutionLedger


def test_claim_persists_record(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")

    record = ledger.claim("hash-1")

    assert record["sha256"] == "hash-1"
    assert record["state"] == "claimed"
    assert ledger.get("hash-1")["state"] == "claimed"


def test_duplicate_claim_is_rejected(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-1")

    with pytest.raises(ValueError, match="already has an execution record"):
        ledger.claim("hash-1")


def test_concurrent_claims_only_allow_one_winner(tmp_path):
    database = tmp_path / "ledger.db"
    SQLiteExecutionLedger(database)

    def try_claim(_):
        ledger = SQLiteExecutionLedger(database)
        try:
            ledger.claim("shared-hash")
            return "claimed"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(try_claim, range(8)))

    assert results.count("claimed") == 1
    assert results.count("rejected") == 7


def test_mark_published(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-1")

    record = ledger.mark_published("hash-1", "media-123")

    assert record["state"] == "published"
    assert record["instagram_media_id"] == "media-123"


def test_uncertain_outcome_cannot_be_claimed_again(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-1")
    ledger.mark_uncertain("hash-1", "Network outcome unknown")

    with pytest.raises(ValueError, match="already has an execution record"):
        ledger.claim("hash-1")


def test_invalid_transition_is_rejected(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-1")
    ledger.mark_published("hash-1", "media-123")

    with pytest.raises(ValueError, match="Transition"):
        ledger.mark_failed("hash-1", "overwrite attempt")


def test_empty_media_id_is_rejected(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-1")

    with pytest.raises(ValueError, match="media ID"):
        ledger.mark_published("hash-1", "")


def test_corrupt_database_is_not_silently_recreated(tmp_path):
    database = tmp_path / "ledger.db"
    database.write_bytes(b"this is not a SQLite database")

    with pytest.raises(sqlite3.DatabaseError):
        SQLiteExecutionLedger(database)


def test_recovery_audit_table_is_initialized(tmp_path):
    database = tmp_path / "ledger.db"
    SQLiteExecutionLedger(database)

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    assert "executions" in tables
    assert "recovery_audit" in tables


def test_recovery_resolution_requires_operator_and_reason(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-recovery")

    with pytest.raises(ValueError):
        ledger.resolve_not_published(
            "hash-recovery",
            operator="",
            reason="Verified that no post exists",
        )

    with pytest.raises(ValueError):
        ledger.resolve_not_published(
            "hash-recovery",
            operator="operator-1",
            reason="",
        )


def test_recovery_resolution_is_audited_and_not_retryable(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "ledger.db")
    ledger.claim("hash-recovery")
    ledger.mark_uncertain("hash-recovery", "Network outcome unknown")

    ledger.resolve_not_published(
        "hash-recovery",
        operator="operator-1",
        reason="Verified in Instagram that the post was not published",
    )

    assert ledger.get("hash-recovery")["state"] == "failed"

    with pytest.raises(ValueError, match="already has an execution record"):
        ledger.claim("hash-recovery")

    with sqlite3.connect(tmp_path / "ledger.db") as connection:
        rows = connection.execute(
            """
            SELECT sha256, prior_state, resolution, operator, reason
            FROM recovery_audit
            WHERE sha256 = ?
            """,
            ("hash-recovery",),
        ).fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "hash-recovery"
    assert rows[0][1] == "uncertain"
    assert rows[0][2] == "not_published"
    assert rows[0][3] == "operator-1"
    assert "Verified in Instagram" in rows[0][4]
