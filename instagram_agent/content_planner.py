
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from core.model import JammerModel
from instagram_agent.media_scanner import load_state, save_state

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_FILE = PROJECT_ROOT / "instagram_agent" / "queue" / "content_plan.json"

CONTENT_PILLARS = [
    "AI explained simply",
    "practical coding and technology tips",
    "local AI and privacy",
    "building Jammer AI in public",
    "useful developer tools",
    "thought-provoking AI questions",
    "short technology tutorials",
]

SYSTEM_PROMPT = """
You are Jammer AI, an AI assistant powered locally by Qwen3-4B.
You create original, accurate Instagram content for @jammeraiagent.

Rules:
- Be clear that you are an AI, not a human.
- Use the supplied content theme and media description.
- Do not invent events, metrics, features, or completed work.
- Do not claim that content has already been published.
- Do not claim that you can add music or edit media unless told so.
- Create varied, useful content rather than repeating introductions.
- Use a strong opening, natural language, and a relevant call to action.
- Include 3 to 5 relevant hashtags.
- Keep the caption below 1,000 characters.
- Return only the caption, with no explanation or quotation marks.
"""


def clean_caption(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip().strip('"').strip("'").strip()

    if not text:
        raise ValueError("The model generated an empty caption.")

    if len(text) > 2200:
        raise ValueError("Generated caption exceeds Instagram's limit.")

    return text


def load_plan():
    if not PLAN_FILE.exists():
        return []

    with PLAN_FILE.open("r", encoding="utf-8") as file:
        plan = json.load(file)

    if not isinstance(plan, list):
        raise RuntimeError("Content plan must contain a JSON list.")

    return plan


def save_plan(plan):
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = PLAN_FILE.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(plan, file, indent=2, ensure_ascii=False)

    temporary.replace(PLAN_FILE)


def generate_caption(model, content_type, media_path):
    themes = CONTENT_PILLARS.copy()
    random.shuffle(themes)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Content type: {content_type}\n"
                f"Media file name: {Path(media_path).name}\n"
                f"Content theme: {themes[0]}\n\n"
                "Write a caption appropriate for this format. "
                "The file name is context only; do not assume you "
                "have visually inspected the media. Avoid inventing "
                "specific details about its contents."
            ),
        },
    ]

    return clean_caption(model.generate(messages, max_tokens=300))


def plan_discovered_media(model=None):
    """
    Generate content plans for discovered media.
    This function does not upload or publish media.
    """
    state = load_state()
    plan = load_plan()

    planned_hashes = {
        item.get("sha256")
        for item in plan
    }

    discovered = [
        (digest, item)
        for digest, item in state["processed"].items()
        if item.get("status") == "discovered"
        and digest not in planned_hashes
    ]

    if not discovered:
        return []

    if model is None:
        model = JammerModel()

    new_items = []

    for digest, item in discovered:
        caption = generate_caption(
            model,
            item["content_type"],
            item["source_path"],
        )

        plan_item = {
            "sha256": digest,
            "media_path": item["source_path"],
            "content_type": item["content_type"],
            "caption": caption,
            "status": "planned",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scheduled_for": None,
            "published_media_id": None,
        }

        plan.append(plan_item)
        new_items.append(plan_item)

    save_plan(plan)
    return new_items


def main():
    print("Jammer AI Content Planner")
    print("Local model generation; no publishing requests.")

    generated = plan_discovered_media()

    if not generated:
        print("No newly discovered media needs a caption.")
        return

    for item in generated:
        print("\nContent type:", item["content_type"])
        print("Media:", item["media_path"])
        print("Status:", item["status"])
        print("\nCaption:\n")
        print(item["caption"])

    print("\nPlans saved. Nothing was published.")


if __name__ == "__main__":
    main()
