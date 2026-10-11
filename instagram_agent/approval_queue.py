
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = PROJECT_ROOT / "instagram_agent" / "queue"
QUEUE_FILE = QUEUE_DIR / "approval_queue.json"

VALID_CONTENT_TYPES = {
    "post",
    "story",
    "reel",
    "comment_reply",
    "message_reply",
}
VALID_STATUSES = {
    "pending",
    "approved",
    "rejected",
    "publishing",
    "published",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ApprovalQueue:
    """Local JSON queue for human-reviewed Instagram content."""

    def __init__(self, queue_file=QUEUE_FILE):
        self.queue_file = Path(queue_file)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.queue_file.exists():
            self._save([])

    def _load(self):
        try:
            with self.queue_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Approval queue JSON is invalid. Preserve the file "
                "and repair it before continuing."
            ) from error

        if not isinstance(data, list):
            raise RuntimeError("Approval queue must contain a JSON list.")

        for item in data:
            if not isinstance(item, dict):
                raise RuntimeError("Queue contains an invalid draft.")
            if item.get("status") not in VALID_STATUSES:
                raise RuntimeError("Queue contains an invalid draft status.")

        return data

    def _save(self, items):
        temporary_file = self.queue_file.with_suffix(".tmp")
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(items, file, indent=2, ensure_ascii=False)
        temporary_file.replace(self.queue_file)

    def add_draft(self, content_type, caption, media_path=None):
        if content_type not in VALID_CONTENT_TYPES:
            raise ValueError(f"Unsupported content type: {content_type}")

        if not isinstance(caption, str) or not caption.strip():
            raise ValueError("Caption or reply text cannot be empty.")

        if media_path is not None and not isinstance(media_path, str):
            raise TypeError("media_path must be a string or None.")

        items = self._load()

        draft = {
            "id": str(uuid.uuid4()),
            "content_type": content_type,
            "caption": caption.strip(),
            "media_path": media_path,
            "status": "pending",
            "created_at": utc_now(),
            "reviewed_at": None,
            "publishing_started_at": None,
            "published_at": None,
            "instagram_media_id": None,
        }

        items.append(draft)
        self._save(items)
        return draft

    def list_drafts(self, status=None):
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        items = self._load()
        if status is not None:
            items = [item for item in items if item["status"] == status]

        return items

    def review_draft(self, draft_id, decision):
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be 'approved' or 'rejected'.")

        items = self._load()

        for item in items:
            if item["id"] == draft_id:
                if item["status"] != "pending":
                    raise ValueError("Only pending drafts can be reviewed.")

                item["status"] = decision
                item["reviewed_at"] = utc_now()

                self._save(items)
                return item

        raise KeyError(f"Draft not found: {draft_id}")

    def get_draft(self, draft_id):
        """Return one draft without changing its status."""
        for item in self._load():
            if item["id"] == draft_id:
                return item

        raise KeyError(f"Draft not found: {draft_id}")

    def begin_publishing(self, draft_id):
        """Claim an approved draft before making an external API request."""
        items = self._load()

        for item in items:
            if item["id"] == draft_id:
                if item["status"] != "approved":
                    raise ValueError(
                        "Only approved drafts can enter publishing."
                    )

                item["status"] = "publishing"
                item["publishing_started_at"] = utc_now()
                self._save(items)
                return item

        raise KeyError(f"Draft not found: {draft_id}")

    def mark_published(self, draft_id, instagram_media_id):
        """Record success only after Instagram returns a media ID."""
        if not isinstance(instagram_media_id, str) or not instagram_media_id.strip():
            raise ValueError("A valid Instagram media ID is required.")

        items = self._load()

        for item in items:
            if item["id"] == draft_id:
                if item["status"] != "publishing":
                    raise ValueError(
                        "Only drafts in publishing status can be completed."
                    )

                item["status"] = "published"
                item["instagram_media_id"] = instagram_media_id.strip()
                item["published_at"] = utc_now()

                self._save(items)
                return item

        raise KeyError(f"Draft not found: {draft_id}")
