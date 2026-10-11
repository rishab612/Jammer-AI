
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from instagram_agent import scheduler


def test_next_slot_uses_india_timezone():
    now = datetime(
        2026, 10, 11, 9, 0,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    slot = scheduler.next_slot("post", now=now)

    assert slot.hour == 10
    assert slot.minute == 0
    assert slot.tzinfo is not None


def test_next_slot_moves_to_next_day_when_time_passed():
    now = datetime(
        2026, 10, 11, 11, 0,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    slot = scheduler.next_slot("post", now=now)

    assert slot.date().isoformat() == "2026-10-12"
    assert slot.hour == 10


def test_next_slot_skips_occupied_slot():
    now = datetime(
        2026, 10, 11, 9, 0,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )
    occupied = [{
        "content_type": "post",
        "scheduled_for": "2026-10-11T10:00:00+05:30",
        "status": "scheduled",
    }]

    slot = scheduler.next_slot("post", now=now, existing=occupied)

    assert slot.date().isoformat() == "2026-10-12"


def test_dry_run_does_not_save_or_publish(tmp_path, monkeypatch):
    plan_file = tmp_path / "content_plan.json"
    schedule_file = tmp_path / "schedule.json"

    plan_file.write_text(json.dumps([{
        "sha256": "test-hash-1",
        "media_path": "sample.jpg",
        "content_type": "post",
        "caption": "Test caption",
    }]), encoding="utf-8")

    monkeypatch.setattr(scheduler, "PLAN_FILE", plan_file)
    monkeypatch.setattr(scheduler, "SCHEDULE_FILE", schedule_file)

    proposed = scheduler.build_schedule(dry_run=True)

    assert len(proposed) == 1
    assert proposed[0]["status"] == "scheduled_dry_run"
    assert proposed[0]["published_media_id"] is None
    assert not schedule_file.exists()


def test_story_waits_for_publisher(tmp_path, monkeypatch):
    plan_file = tmp_path / "content_plan.json"
    schedule_file = tmp_path / "schedule.json"

    plan_file.write_text(json.dumps([{
        "sha256": "story-hash-1",
        "media_path": "story.jpg",
        "content_type": "story",
        "caption": "",
    }]), encoding="utf-8")

    monkeypatch.setattr(scheduler, "PLAN_FILE", plan_file)
    monkeypatch.setattr(scheduler, "SCHEDULE_FILE", schedule_file)

    proposed = scheduler.build_schedule(dry_run=True)

    assert len(proposed) == 1
    assert proposed[0]["status"] == "waiting_for_publisher"


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError):
        scheduler.next_slot(
            "post",
            now=datetime(2026, 10, 11, 9, 0),
        )

def test_feed_posts_are_limited_to_one_per_day():
    now = datetime(
        2026, 10, 12, 9, 0,
        tzinfo=ZoneInfo("Asia/Kolkata"),
    )

    existing = [{
        "content_type": "post",
        "scheduled_for": "2026-10-12T10:00:00+05:30",
        "status": "scheduled",
    }]

    slot = scheduler.next_slot("post", now=now, existing=existing)

    assert slot.date().isoformat() == "2026-10-13"
    assert slot.hour == 10
    assert slot.minute == 0


def test_persistent_schedule_is_saved(tmp_path, monkeypatch):
    plan_file = tmp_path / "content_plan.json"
    schedule_file = tmp_path / "schedule.json"

    plan_file.write_text(json.dumps([{
        "sha256": "persist-hash-1",
        "media_path": "post.jpg",
        "content_type": "post",
        "caption": "Persistent test",
    }]), encoding="utf-8")

    monkeypatch.setattr(scheduler, "PLAN_FILE", plan_file)
    monkeypatch.setattr(scheduler, "SCHEDULE_FILE", schedule_file)

    additions = scheduler.build_schedule(dry_run=False)

    assert len(additions) == 1
    assert schedule_file.exists()

    saved = json.loads(schedule_file.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["sha256"] == "persist-hash-1"
    assert saved[0]["status"] == "scheduled"


def test_existing_media_is_not_scheduled_twice(tmp_path, monkeypatch):
    plan_file = tmp_path / "content_plan.json"
    schedule_file = tmp_path / "schedule.json"

    plan_file.write_text(json.dumps([{
        "sha256": "duplicate-hash-1",
        "media_path": "post.jpg",
        "content_type": "post",
        "caption": "Duplicate test",
    }]), encoding="utf-8")

    existing = [{
        "sha256": "duplicate-hash-1",
        "media_path": "post.jpg",
        "content_type": "post",
        "caption": "Duplicate test",
        "scheduled_for": "2026-10-12T10:00:00+05:30",
        "status": "scheduled",
        "published_media_id": None,
    }]

    schedule_file.write_text(
        json.dumps(existing),
        encoding="utf-8",
    )

    monkeypatch.setattr(scheduler, "PLAN_FILE", plan_file)
    monkeypatch.setattr(scheduler, "SCHEDULE_FILE", schedule_file)

    additions = scheduler.build_schedule(dry_run=False)

    assert additions == []

    saved = json.loads(schedule_file.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["sha256"] == "duplicate-hash-1"
