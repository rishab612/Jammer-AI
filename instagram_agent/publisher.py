
import time

from instagram_agent.approval_queue import ApprovalQueue
from instagram_agent.client import InstagramClient, InstagramAPIError


MAX_STATUS_CHECKS = 10
STATUS_CHECK_INTERVAL_SECONDS = 3


def publish_approved_image(draft_id, image_url):
    """
    Publish one explicitly approved image feed post.

    Live API requests are made only after draft and input validation.
    Publishing is never automatically retried.
    """
    queue = ApprovalQueue()

    # Validate the draft before any network request.
    draft = queue.get_draft(draft_id)

    if draft["status"] != "approved":
        raise ValueError(
            f"Draft must be approved first; current status: {draft['status']}"
        )

    if draft["content_type"] != "post":
        raise ValueError("Only image feed posts are supported here.")

    # Validate the URL before changing the queue state.
    if not isinstance(image_url, str):
        raise ValueError("Image URL must be a string.")

    image_url = image_url.strip()

    if not image_url.startswith("https://"):
        raise ValueError("Image URL must use HTTPS.")

    client = InstagramClient()

    # Claim the draft before any publishing workflow starts.
    queue.begin_publishing(draft_id)

    # If the API outcome is uncertain, preserve the publishing state.
    creation_id = client.create_image_container(
        image_url=image_url,
        caption=draft["caption"],
    )

    # Poll for a bounded time while Instagram processes the image.
    status = {}

    for attempt in range(MAX_STATUS_CHECKS):
        status = client.get_container_status(creation_id)
        status_code = status.get("status_code")

        if status_code == "FINISHED":
            break

        if status_code in {"ERROR", "EXPIRED"}:
            raise InstagramAPIError(
                f"Instagram media container status: {status_code}. "
                "No publish request was made. Inspect the draft and "
                "container before taking further action."
            )

        if attempt < MAX_STATUS_CHECKS - 1:
            time.sleep(STATUS_CHECK_INTERVAL_SECONDS)
    else:
        last_status = status.get("status_code") or "unknown"
        raise InstagramAPIError(
            "Media container did not become ready within the polling "
            f"limit. Last status: {last_status}. No publish request "
            "was made. Inspect the container before continuing."
        )

    # A single live publish request. Never retry automatically.
    media_id = client.publish_container(creation_id)

    # Record success only after Instagram returns a media ID.
    queue.mark_published(draft_id, media_id)

    return media_id


def main():
    print("Jammer AI Instagram Publisher")
    print("WARNING: This tool can publish a live Instagram post.")

    draft_id = input(
        "Enter the explicitly approved draft ID: "
    ).strip()

    image_url = input(
        "Enter the publicly accessible HTTPS image URL: "
    ).strip()

    confirmation = input(
        "Type PUBLISH to authorize a live Instagram publishing request: "
    ).strip()

    if confirmation != "PUBLISH":
        print("Cancelled. No publishing request was made.")
        return

    try:
        media_id = publish_approved_image(draft_id, image_url)
        print("Instagram confirmed publication.")
        print("Instagram media ID:", media_id)

    except (ValueError, KeyError, InstagramAPIError) as error:
        print("Publishing stopped:", error)
        print(
            "Inspect the draft status and Instagram account before "
            "attempting any further action. Do not blindly retry."
        )


if __name__ == "__main__":
    main()
