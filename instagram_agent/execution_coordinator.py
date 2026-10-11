
from instagram_agent.sqlite_ledger import SQLiteExecutionLedger


class ExecutionCoordinator:
    """
    Coordinates execution state using SQLite.

    This module does not publish to Instagram. A claim prevents duplicate
    local execution, but it cannot guarantee exactly-once external publishing.
    """

    def __init__(self, ledger=None):
        self.ledger = ledger or SQLiteExecutionLedger()

    def claim(self, sha256):
        """Claim media once; reject any media with an existing record."""
        return self.ledger.claim(sha256)

    def record_published(self, sha256, instagram_media_id):
        """Record confirmed publication."""
        return self.ledger.mark_published(
            sha256,
            instagram_media_id,
        )

    def record_failed(self, sha256, error):
        """Record a definite failure before external publication."""
        return self.ledger.mark_failed(sha256, error)

    def record_uncertain(self, sha256, error):
        """
        Record an ambiguous outcome.

        Uncertain records must be inspected manually; do not retry them
        automatically.
        """
        return self.ledger.mark_uncertain(sha256, error)

    def inspect(self, sha256):
        """Return the current execution record, or None if absent."""
        return self.ledger.get(sha256)

    
    def list_recovery_items(self):
        """
        List claimed or uncertain executions requiring manual review.

        This method is read-only and never retries or changes records.
        """
        return self.ledger.list_by_states({"claimed", "uncertain"})


    def can_attempt(self, sha256):
        """
        Return True only when no execution record exists.

        This is an informational check, not a reservation. Always call
        claim() to atomically reserve media before any future execution.
        """
        return self.inspect(sha256) is None
