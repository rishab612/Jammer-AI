
import pytest

from instagram_agent.execution_coordinator import ExecutionCoordinator
from instagram_agent.sqlite_ledger import SQLiteExecutionLedger


@pytest.fixture
def coordinator(tmp_path):
    ledger = SQLiteExecutionLedger(tmp_path / "coordinator_test.db")
    return ExecutionCoordinator(ledger=ledger)


def test_claim_creates_record(coordinator):
    digest = "a" * 64

    record = coordinator.claim(digest)

    assert record["sha256"] == digest
    assert record["state"] == "claimed"
    assert coordinator.inspect(digest)["state"] == "claimed"


def test_duplicate_claim_is_rejected(coordinator):
    digest = "b" * 64
    coordinator.claim(digest)

    with pytest.raises(ValueError, match="already has an execution record"):
        coordinator.claim(digest)


def test_confirmed_publication_is_recorded(coordinator):
    digest = "c" * 64
    coordinator.claim(digest)

    record = coordinator.record_published(digest, "test-media-123")

    assert record["state"] == "published"
    assert record["instagram_media_id"] == "test-media-123"
    assert coordinator.can_attempt(digest) is False


def test_definite_failure_is_recorded_without_retry(coordinator):
    digest = "d" * 64
    coordinator.claim(digest)

    record = coordinator.record_failed(digest, "Simulated pre-publish failure")

    assert record["state"] == "failed"
    assert "Simulated pre-publish failure" in record["last_error"]
    assert coordinator.can_attempt(digest) is False


def test_uncertain_outcome_is_not_retryable(coordinator):
    digest = "e" * 64
    coordinator.claim(digest)

    record = coordinator.record_uncertain(
        digest,
        "Simulated ambiguous response",
    )

    assert record["state"] == "uncertain"
    assert coordinator.can_attempt(digest) is False

    with pytest.raises(ValueError, match="already has an execution record"):
        coordinator.claim(digest)


def test_cannot_mark_unclaimed_media_as_published(coordinator):
    with pytest.raises(ValueError, match="Transition to 'published' rejected"):
        coordinator.record_published("f" * 64, "test-media-456")


def test_empty_media_hash_is_rejected(coordinator):
    with pytest.raises(ValueError, match="sha256 must be a non-empty string"):
        coordinator.claim("")


def test_empty_media_id_is_rejected(coordinator):
    digest = "g" * 64
    coordinator.claim(digest)

    with pytest.raises(ValueError, match="valid Instagram media ID"):
        coordinator.record_published(digest, "")


from concurrent.futures import ThreadPoolExecutor


def test_concurrent_claims_only_allow_one_winner(tmp_path):
    database = tmp_path / "concurrent_coordinator.db"
    digest = "h" * 64

    def attempt_claim():
        coordinator = ExecutionCoordinator(
            ledger=SQLiteExecutionLedger(database)
        )
        try:
            coordinator.claim(digest)
            return "claimed"
        except ValueError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: attempt_claim(), range(8)))

    assert results.count("claimed") == 1
    assert results.count("rejected") == 7

    final_record = SQLiteExecutionLedger(database).get(digest)
    assert final_record["state"] == "claimed"


def test_interrupted_claim_is_not_automatically_retried(tmp_path):
    database = tmp_path / "interrupted_execution.db"
    digest = "i" * 64

    # Simulate a process claiming media and then stopping.
    first = ExecutionCoordinator(
        ledger=SQLiteExecutionLedger(database)
    )
    first.claim(digest)

    # A newly created coordinator represents a restarted worker.
    restarted = ExecutionCoordinator(
        ledger=SQLiteExecutionLedger(database)
    )

    record = restarted.inspect(digest)

    assert record is not None
    assert record["state"] == "claimed"
    assert restarted.can_attempt(digest) is False

    with pytest.raises(ValueError, match="already has an execution record"):
        restarted.claim(digest)


def test_recovery_inspection_lists_claimed_and_uncertain(coordinator):
    claimed_hash = "j" * 64
    uncertain_hash = "k" * 64

    coordinator.claim(claimed_hash)
    coordinator.claim(uncertain_hash)
    coordinator.record_uncertain(uncertain_hash, "Simulated ambiguous outcome")

    items = coordinator.list_recovery_items()
    by_hash = {item["sha256"]: item for item in items}

    assert set(by_hash) == {claimed_hash, uncertain_hash}
    assert by_hash[claimed_hash]["state"] == "claimed"
    assert by_hash[uncertain_hash]["state"] == "uncertain"


def test_recovery_inspection_does_not_change_records(coordinator):
    digest = "l" * 64
    coordinator.claim(digest)

    before = coordinator.inspect(digest)
    coordinator.list_recovery_items()
    after = coordinator.inspect(digest)

    assert after == before
    assert after["state"] == "claimed"
