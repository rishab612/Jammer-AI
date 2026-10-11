
from instagram_agent.client import InstagramClient, InstagramAPIError


def main():
    try:
        client = InstagramClient()
        profile = client.get_profile()

        # Print only non-secret profile information.
        print("Instagram connection: SUCCESS")
        print("Username:", profile.get("username", "(not returned)"))
        print("User ID:", profile.get("user_id", "(not returned)"))

    except (ValueError, InstagramAPIError) as error:
        print("Instagram connection: FAILED")
        print(error)


if __name__ == "__main__":
    main()
