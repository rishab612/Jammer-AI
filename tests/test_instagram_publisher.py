
import pytest

from instagram_agent import publisher
from instagram_agent.approval_queue import ApprovalQueue
from instagram_agent.client import InstagramAPIError


IMAGE_URL = "https://example.com/test-image.jpg"


class FakeInstagramClient:
    """Fake client: never makes network requests."""

    instances = []

    def __init__(self):
        self.statuses = []
        self.created = []
        self.published = []
        self.instances.append(self)

    def create_image_container(self, image_url, caption):
        self.created.append((image_url, caption))
        return "fake-container-123"

    def get_container_status(self, creation_id):
        assert creation_id == "fake-container-123"
        if not self.statuses:
            return {"status_code": "FINISHED"}
        return {"status_code": self.statuses.pop(0)}

    def publish_container(self, creation_id):
        self.published.append(creation_id)
        return "fake-media-456"


@pytest.fixture
def setup_publisher(tmp_path, monkeypatch):
    queue_file = tmp_path / "approval_queue.json"
    queue = ApprovalQueue(queue_file=queue_file)

    monkeypatch.setattr(
        publisher, "ApprovalQueue", lambda: queue
    )
    monkeypatch.setattr(
        publisher, "InstagramClient", FakeInstagramClient
    )
    monkeypatch.setattr(
        publisher.time, "sleep", lambda seconds: None
    )

    FakeInstagramClient.instances.clear()

    return queue


def add_draft(queue, status="approved", content_type="post"):
    draft = queue.add_draft(
        content_type=content_type,
        caption="Offline test caption",
    )

    if status == "approved":
        queue.review_draft(draft["id"], "approved")

    return draft


def test_unapproved_draft_is_rejected_before_client_creation(
    setup_publisher,
):
    queue = setup_publisher
    draft = add_draft(queue, status="pending")

    with pytest.raises(ValueError, match="approved first"):
        publisher.publish_approved_image(draft["id"], IMAGE_URL)

    assert FakeInstagramClient.instances == []
    assert queue.get_draft(draft["id"])["status"] == "pending"


def test_non_post_content_is_rejected(setup_publisher):
    queue = setup_publisher
    draft = add_draft(queue, content_type="story")

    with pytest.raises(ValueError, match="Only image feed posts"):
        publisher.publish_approved_image(draft["id"], IMAGE_URL)

    assert FakeInstagramClient.instances == []
    assert queue.get_draft(draft["id"])["status"] == "approved"


def test_non_https_url_is_rejected(setup_publisher):
    queue = setup_publisher
    draft = add_draft(queue)

    with pytest.raises(ValueError, match="HTTPS"):
        publisher.publish_approved_image(
            draft["id"], "http://example.com/image.jpg"
        )

    assert FakeInstagramClient.instances == []
    assert queue.get_draft(draft["id"])["status"] == "approved"


def test_finished_container_publishes_once(setup_publisher):
    queue = setup_publisher
    draft = add_draft(queue)

    media_id = publisher.publish_approved_image(
        draft["id"], IMAGE_URL
    )

    client = FakeInstagramClient.instances[0]

    assert media_id == "fake-media-456"
    assert len(client.created) == 1
    assert client.published == ["fake-container-123"]
    assert queue.get_draft(draft["id"])["status"] == "published"


def test_processing_then_finished_publishes_once(setup_publisher):
    queue = setup_publisher
    draft = add_draft(queue)

    def make_client():
        client = FakeInstagramClient()
        client.statuses = ["IN_PROGRESS", "FINISHED"]
        return client

    monkeypatch_client = FakeInstagramClient

    # Configure the fake instance to report processing first.
    original_init = monkeypatch_client.__init__

    def custom_init(self):
        original_init(self)
        self.statuses = ["IN_PROGRESS", "FINISHED"]

    monkeypatch_client.__init__ = custom_init

    try:
        publisher.publish_approved_image(draft["id"], IMAGE_URL)
    finally:
        monkeypatch_client.__init__ = original_init

    client = FakeInstagramClient.instances[-1]
    assert len(client.published) == 1
    assert queue.get_draft(draft["id"])["status"] == "published"


@pytest.mark.parametrize("failure_status", ["ERROR", "EXPIRED"])
def test_failed_container_is_not_published(
    setup_publisher, failure_status
):
    queue = setup_publisher
    draft = add_draft(queue)

    original_init = FakeInstagramClient.__init__

    def custom_init(self):
        original_init(self)
        self.statuses = [failure_status]

    FakeInstagramClient.__init__ = custom_init

    try:
        with pytest.raises(InstagramAPIError, match=failure_status):
            publisher.publish_approved_image(draft["id"], IMAGE_URL)
    finally:
        FakeInstagramClient.__init__ = original_init

    client = FakeInstagramClient.instances[-1]
    assert client.published == []
    assert queue.get_draft(draft["id"])["status"] == "publishing"


def test_container_timeout_does_not_publish(setup_publisher, monkeypatch):
    queue = setup_publisher
    draft = add_draft(queue)

    original_init = FakeInstagramClient.__init__

    def custom_init(self):
        original_init(self)
        self.statuses = ["IN_PROGRESS"] * publisher.MAX_STATUS_CHECKS

    FakeInstagramClient.__init__ = custom_init

    try:
        with pytest.raises(InstagramAPIError, match="polling limit"):
            publisher.publish_approved_image(draft["id"], IMAGE_URL)
    finally:
        FakeInstagramClient.__init__ = original_init

    client = FakeInstagramClient.instances[-1]
    assert client.published == []
    assert queue.get_draft(draft["id"])["status"] == "publishing"
