
from tempfile import TemporaryDirectory
from pathlib import Path

from instagram_agent.approval_queue import ApprovalQueue


def main():
    with TemporaryDirectory() as temp_dir:
        queue = ApprovalQueue(
            queue_file=Path(temp_dir) / "approval_queue.json"
        )

        draft = queue.add_draft(
            content_type="post",
            caption="Local publishing safety test",
            media_path="test-image.jpg",
        )
        draft_id = draft["id"]

        # Pending drafts must not enter publishing.
        try:
            queue.begin_publishing(draft_id)
            raise AssertionError("Pending draft was incorrectly allowed.")
        except ValueError:
            print("PASS: Pending draft cannot enter publishing.")

        # Explicit approval is required.
        queue.review_draft(draft_id, "approved")
        queue.begin_publishing(draft_id)
        print("PASS: Approved draft enters publishing state.")

        # A media ID is required to mark success.
        try:
            queue.mark_published(draft_id, "")
            raise AssertionError("Empty media ID was incorrectly accepted.")
        except ValueError:
            print("PASS: Empty Instagram media ID is rejected.")

        queue.mark_published(draft_id, "TEST_MEDIA_ID")
        result = queue.list_drafts(status="published")

        assert len(result) == 1
        assert result[0]["instagram_media_id"] == "TEST_MEDIA_ID"
        print("PASS: Published state records the media ID.")

        # A published draft cannot be published again through the queue.
        try:
            queue.begin_publishing(draft_id)
            raise AssertionError("Published draft was allowed again.")
        except ValueError:
            print("PASS: Published draft cannot re-enter publishing.")

        print("\nAll local publishing safety checks passed.")


if __name__ == "__main__":
    main()
