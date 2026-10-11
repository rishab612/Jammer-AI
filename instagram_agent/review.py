
from instagram_agent.approval_queue import ApprovalQueue


def main():
    queue = ApprovalQueue()

    while True:
        print("\n=== JAMMER AI - INSTAGRAM REVIEW ===")
        print("1. List pending drafts")
        print("2. Approve a draft")
        print("3. Reject a draft")
        print("4. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            drafts = queue.list_drafts(status="pending")

            if not drafts:
                print("No pending drafts.")
                continue

            for draft in drafts:
                print("\nID:", draft["id"])
                print("Type:", draft["content_type"])
                print("Caption:", draft["caption"])
                print("Media:", draft.get("media_path") or "None")
                print("Status:", draft["status"])

        elif choice in {"2", "3"}:
            draft_id = input("Enter the draft ID: ").strip()
            decision = "approved" if choice == "2" else "rejected"

            try:
                draft = queue.review_draft(draft_id, decision)
                print(f"Draft {decision}: {draft['id']}")
            except (KeyError, ValueError) as error:
                print("Could not review draft:", error)

        elif choice == "4":
            print("Review closed. No Instagram action was performed.")
            break

        else:
            print("Invalid option. Choose 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
