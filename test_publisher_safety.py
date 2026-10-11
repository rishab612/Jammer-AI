
from instagram_agent.publisher import publish_approved_image
from instagram_agent.approval_queue import ApprovalQueue


def main():
    queue = ApprovalQueue()

    draft = queue.add_draft(
        content_type="post",
        caption="Publisher safety test only",
    )

    print("Test draft ID:", draft["id"])
    print("Status:", draft["status"])

    try:
        publish_approved_image(
            draft_id=draft["id"],
            image_url="https://example.com/test.jpg",
        )
    except ValueError as error:
        print("Safely rejected:", error)
    else:
        raise AssertionError(
            "A pending draft was unexpectedly accepted."
        )

    # Verify the test draft remains pending.
    saved_draft = queue.get_draft(draft["id"])
    assert saved_draft["status"] == "pending"

    print("PASS: No publishing request was made.")
    print("PASS: Draft remains pending.")


if __name__ == "__main__":
    main()
