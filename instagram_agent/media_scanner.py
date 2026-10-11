
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOX = PROJECT_ROOT / "instagram_agent" / "inbox"
STATE_FILE = PROJECT_ROOT / "instagram_agent" / "queue" / "media_state.json"

FOLDERS = {
    "post": INBOX / "posts",
    "story": INBOX / "stories",
    "reel": INBOX / "reels",
}

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"
}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state():
    if not STATE_FILE.exists():
        return {"processed": {}}

    with STATE_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(
        data.get("processed"), dict
    ):
        raise RuntimeError("Media state file has an invalid structure.")

    return data


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)

    temporary.replace(STATE_FILE)


def scan_media():
    """Find supported files without uploading, moving, or publishing them."""
    state = load_state()
    seen_hashes = {
        item.get("sha256")
        for item in state["processed"].values()
    }

    discovered = []

    for content_type, folder in FOLDERS.items():
        folder.mkdir(parents=True, exist_ok=True)

        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue

            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            try:
                digest = sha256_file(path)
            except OSError:
                continue

            if digest in seen_hashes:
                continue

            discovered.append({
                "path": str(path),
                "content_type": content_type,
                "sha256": digest,
                "size_bytes": path.stat().st_size,
            })

            seen_hashes.add(digest)

    return discovered


def record_media(item):
    """Record discovery; does not claim the item was published."""
    state = load_state()
    digest = item["sha256"]

    if digest in state["processed"]:
        return False

    state["processed"][digest] = {
        "source_path": item["path"],
        "content_type": item["content_type"],
        "status": "discovered",
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }

    save_state(state)
    return True


def main():
    print("Jammer AI Media Scanner")
    print("Scan-only mode: no uploads or publications.")

    items = scan_media()

    if not items:
        print("No new supported media files found.")
        return

    for item in items:
        print()
        print("Type:", item["content_type"])
        print("File:", item["path"])
        print("Size:", item["size_bytes"], "bytes")
        print("SHA-256:", item["sha256"])

        if record_media(item):
            print("Recorded: discovered")
        else:
            print("Already recorded; skipped")

    print()
    print("Scan complete. Nothing was published.")


if __name__ == "__main__":
    main()
