
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_FILE = PROJECT_ROOT / "instagram_agent" / "queue" / "content_plan.json"
SCHEDULE_FILE = PROJECT_ROOT / "instagram_agent" / "queue" / "schedule.json"

TIMEZONE_NAME = "Asia/Kolkata"

# Target local posting times. These are configurable defaults,
# not claims about the best engagement times for your account.
DAILY_TIMES = {
    "post": time(10, 0),
    "story": time(18, 0),
}

SUPPORTED_SCHEDULE_TYPES = {"post", "story", "reel"}


def load_json_list(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise RuntimeError(f"{path.name} must contain a JSON list.")

    return data


def save_json_list(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    temporary.replace(path)



def next_slot(content_type, now=None, existing=None):
    """Return the next available slot, respecting daily posting limits."""
    if content_type not in SUPPORTED_SCHEDULE_TYPES:
        raise ValueError(f"Unsupported content type: {content_type}")

    zone = ZoneInfo(TIMEZONE_NAME)
    now = now or datetime.now(zone)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware.")

    now = now.astimezone(zone)
    existing = existing or []

    active_statuses = {
        "scheduled",
        "scheduled_dry_run",
        "waiting_for_publisher",
        "publishing",
        "published",
    }

    for day_offset in range(0, 31):
        day = now.date() + timedelta(days=day_offset)
        slot_time = DAILY_TIMES.get(content_type, time(20, 0))
        candidate = datetime.combine(day, slot_time, tzinfo=zone)

        if candidate <= now:
            continue

        same_day_items = []

        for item in existing:
            if item.get("content_type") != content_type:
                continue

            if item.get("status") not in active_statuses:
                continue

            scheduled_text = item.get("scheduled_for")
            if not scheduled_text:
                continue

            try:
                scheduled = datetime.fromisoformat(scheduled_text)
            except (TypeError, ValueError):
                raise RuntimeError(
                    f"Invalid scheduled_for value in queue: {scheduled_text!r}"
                )

            if scheduled.tzinfo is None or scheduled.utcoffset() is None:
                raise RuntimeError(
                    f"Schedule timestamp has no timezone: {scheduled_text!r}"
                )

            if scheduled.astimezone(zone).date() == day:
                same_day_items.append(item)

        # Enforce at most one feed post per local calendar day.
        if content_type == "post" and same_day_items:
            continue

        # Stories and Reels may have different daily slots, but not
        # two items of the same type at the same exact time.
        if any(
            datetime.fromisoformat(item["scheduled_for"]).astimezone(zone)
            == candidate
            for item in same_day_items
        ):
            continue

        return candidate

    raise RuntimeError(
        f"No available {content_type} slot found in the next 31 days."
    )


def build_schedule(dry_run=True):
    """
    Build a persistent schedule without publishing anything.

    Dry runs do not write to the schedule file.
    Active scheduled and published media are never automatically
    re-added, even if a previous item failed or was cancelled.
    """
    plan = load_json_list(PLAN_FILE)
    schedule = load_json_list(SCHEDULE_FILE)

    # Preserve every previously recorded media hash, including failed
    # and cancelled entries. Retries should be explicit, not automatic.
    already_recorded = {
        item.get("sha256")
        for item in schedule
        if item.get("sha256")
    }

    additions = []
    working_schedule = list(schedule)

    for item in plan:
        digest = item.get("sha256")
        content_type = item.get("content_type")

        if not digest or digest in already_recorded:
            continue

        if content_type not in SUPPORTED_SCHEDULE_TYPES:
            continue

        slot = next_slot(content_type, existing=working_schedule)

        if content_type == "post":
            status = "scheduled_dry_run" if dry_run else "scheduled"
        else:
            # Stories and Reels cannot publish until their official
            # API workflows are implemented and tested.
            status = "waiting_for_publisher"

        entry = {
            "sha256": digest,
            "media_path": item.get("media_path"),
            "content_type": content_type,
            "caption": item.get("caption", ""),
            "scheduled_for": slot.isoformat(),
            "status": status,
            "published_media_id": None,
        }

        additions.append(entry)
        working_schedule.append(entry)
        already_recorded.add(digest)

    if not dry_run and additions:
        save_json_list(SCHEDULE_FILE, working_schedule)

    if dry_run and additions:
        print("Dry run: proposed schedule was not saved.")

    return additions



def main():
    print("Jammer AI Scheduler")
    print("Timezone:", TIMEZONE_NAME)
    print("Mode: DRY RUN — no Instagram requests.")

    proposed = build_schedule(dry_run=True)

    if not proposed:
        print("No new planned content to schedule.")
        return

    for item in proposed:
        print()
        print("Type:", item["content_type"])
        print("Scheduled for:", item["scheduled_for"])
        print("Status:", item["status"])
        print("Media:", item["media_path"])

    print()
    print("Dry run complete. Nothing was published or saved.")


if __name__ == "__main__":
    main()
