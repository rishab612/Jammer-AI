
import json

import pytest

from instagram_agent.execution_ledger import ExecutionLedger


def test_claim_creates_persistent_record(tmp_path):
    path = tmp_path / "execution_ledger.json"
    ledger = ExecutionLedger(path)

    record = ledger.claim("hash-1")

    assert record["sha256"] == "hash-1"
    assert record["state"] == "claimed"
    assert record["instagram_media_id"] is None

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["state"] == "claimed"


def test_duplicate_claim_is_rejected(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.json")
    ledger.claim("hash-1")

    with pytest.raises(ValueError, match="already recorded"):
        ledger.claim("hash-1")


def test_claim_can_be_marked_published(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.json")
    ledger.claim("hash-1")

    record = ledger.mark_published("hash-1", "instagram-media-123")

    assert record["state"] == "published"
    assert record["instagram_media_id"] == "instagram-media-123"
    assert ledger.get("hash-1")["state"] == "published"


def test_claim_can_be_marked_failed(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.json")
    ledger.claim("hash-1")

    record = ledger.mark_failed("hash-1", "Confirmed validation failure")

    assert record["state"] == "failed"
    assert record["last_error"] == "Confirmed validation failure"


def test_claim_can_be_marked_uncertain(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.json")
    ledger.claim("hash-1")

    record = ledger.mark_uncertain("hash-1", "Network outcome unknown")

    assert record["state"] == "uncertain"

    with pytest.raises(ValueError, match="already recorded"):
        ledger.claim("hash-1")


def test_invalid_transition_is_rejected(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.json")
    ledger.claim("hash-1")
    ledger.mark_published("hash-1", "instagram-media-123")

    with pytest.raises(ValueError, match="expected"):
        ledger.mark_failed("hash-1", "Attempt to overwrite success")


def test_invalid_media_id_is_rejected(tmp_path):
    ledger = ExecutionLedger(tmp_path / "ledger.json")
    ledger.claim("hash-1")

    with pytest.raises(ValueError, match="media ID"):
        ledger.mark_published("hash-1", "")


def test_corrupt_ledger_fails_closed(tmp_path):
    path = tmp_path / "ledger.json"
    path.write_text("{invalid json", encoding="utf-8")
    ledger = ExecutionLedger(path)

    with pytest.raises(RuntimeError, match="invalid"):
        ledger.get("hash-1")
