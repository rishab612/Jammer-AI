
import json

from instagram_agent import content_planner
from instagram_agent.media_scanner import scan_media, record_media


class FakeModel:
    """Fake local model so tests never load Qwen."""

    def __init__(self):
        self.calls = 0

    def generate(self, messages, max_tokens=512):
        self.calls += 1
        return "A useful AI tip for your day. #JammerAI #LocalAI"


def configure_temporary_paths(tmp_path, monkeypatch):
    """Keep test media and state completely separate from project data."""
    inbox = tmp_path / "inbox"
    posts = inbox / "posts"
    stories = inbox / "stories"
    reels = inbox / "reels"

    posts.mkdir(parents=True)
    stories.mkdir(parents=True)
    reels.mkdir(parents=True)

    state_file = tmp_path / "media_state.json"
    plan_file = tmp_path / "content_plan.json"

    monkeypatch.setattr(
        "instagram_agent.media_scanner.INBOX",
        inbox,
    )
    monkeypatch.setattr(
        "instagram_agent.media_scanner.FOLDERS",
        {
            "post": posts,
            "story": stories,
            "reel": reels,
        },
    )
    monkeypatch.setattr(
        "instagram_agent.media_scanner.STATE_FILE",
        state_file,
    )
    monkeypatch.setattr(
        content_planner,
        "PLAN_FILE",
        plan_file,
    )

    return posts, stories, reels, state_file, plan_file


def test_caption_cleaning():
    result = content_planner.clean_caption(
        "  Useful tip. #JammerAI  "
    )

    assert result == "Useful tip. #JammerAI"


def test_empty_caption_rejected():
    try:
        content_planner.clean_caption("   ")
    except ValueError:
        pass
    else:
        raise AssertionError("An empty caption should be rejected.")


def test_planner_creates_plan_without_publishing(
    tmp_path, monkeypatch
):
    posts, _, _, state_file, plan_file = configure_temporary_paths(
        tmp_path, monkeypatch
    )

    # Fake media bytes are enough to test scanning and hashing.
    # No image decoding or Instagram upload takes place.
    media = posts / "test.jpg"
    media.write_bytes(b"fake image bytes")

    items = scan_media()

    assert len(items) == 1
    assert items[0]["content_type"] == "post"
    assert record_media(items[0]) is True

    model = FakeModel()

    planned = content_planner.plan_discovered_media(model=model)

    assert len(planned) == 1
    assert planned[0]["status"] == "planned"
    assert planned[0]["content_type"] == "post"
    assert planned[0]["caption"].startswith("A useful AI tip")
    assert planned[0]["published_media_id"] is None
    assert model.calls == 1

    saved = json.loads(plan_file.read_text(encoding="utf-8"))

    assert len(saved) == 1
    assert saved[0]["status"] == "planned"
    assert saved[0]["published_media_id"] is None

    # The media state remains a discovery record.
    state = json.loads(state_file.read_text(encoding="utf-8"))
    digest = items[0]["sha256"]

    assert state["processed"][digest]["status"] == "discovered"


def test_planner_does_not_plan_same_media_twice(
    tmp_path, monkeypatch
):
    posts, _, _, _, plan_file = configure_temporary_paths(
        tmp_path, monkeypatch
    )

    media = posts / "test.jpg"
    media.write_bytes(b"fake image bytes")

    items = scan_media()

    assert len(items) == 1
    assert record_media(items[0]) is True

    model = FakeModel()

    first = content_planner.plan_discovered_media(model=model)
    second = content_planner.plan_discovered_media(model=model)

    assert len(first) == 1
    assert second == []
    assert model.calls == 1

    saved = json.loads(plan_file.read_text(encoding="utf-8"))
    assert len(saved) == 1
