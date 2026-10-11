
from instagram_agent.approval_queue import ApprovalQueue


def main():
    queue = ApprovalQueue()

    draft = queue.add_draft(
        content_type="post",
        caption=(
            "Hello from Jammer AI! "
            "A new chapter in my local AI journey."
        ),
    )

    print("Draft created.")
    print("Draft ID:", draft["id"])
    print("Status:", draft["status"])
    print("Content type:", draft["content_type"])
    print("Caption:", draft["caption"])

    pending = queue.list_drafts(status="pending")
    print("Pending drafts:", len(pending))

    # Intentionally do not approve or publish anything in this test.


if __name__ == "__main__":
    main()
