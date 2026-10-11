
import os

import requests
from dotenv import load_dotenv


load_dotenv()

GRAPH_API_BASE = "https://graph.instagram.com"
API_VERSION = "v25.0"


class InstagramAPIError(RuntimeError):
    """Raised when an Instagram API request fails."""


class InstagramClient:
    """Instagram API client using Instagram Login."""

    def __init__(self):
        self.access_token = os.getenv(
            "INSTAGRAM_ACCESS_TOKEN", ""
        ).strip()
        self.user_id = os.getenv(
            "INSTAGRAM_USER_ID", ""
        ).strip()

        if (
            not self.access_token
            or self.access_token == "PASTE_YOUR_TOKEN_HERE"
        ):
            raise ValueError(
                "INSTAGRAM_ACCESS_TOKEN is missing from the local .env file."
            )

        if not self.user_id:
            raise ValueError(
                "INSTAGRAM_USER_ID is missing from the local .env file."
            )

        self.session = requests.Session()

    def _request(self, method, endpoint, data=None, params=None):
        """Make an API request without exposing the access token in errors."""
        url = (
            f"{GRAPH_API_BASE}/"
            f"{API_VERSION}/{endpoint.lstrip('/')}"
        )

        request_data = dict(data or {})
        request_params = dict(params or {})

        # Send the token in the request body for POST requests
        # and as a query parameter for GET requests.
        if method.upper() == "POST":
            request_data["access_token"] = self.access_token
        else:
            request_params["access_token"] = self.access_token

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                data=request_data if method.upper() == "POST" else None,
                params=request_params if method.upper() != "POST" else None,
                timeout=30,
            )
        except requests.RequestException as error:
            # Avoid including request URLs or token-bearing parameters.
            raise InstagramAPIError(
                f"Instagram network request failed: "
                f"{type(error).__name__}"
            ) from None

        try:
            result = response.json()
        except ValueError:
            result = {}

        if not response.ok:
            details = (
                result.get("error", {})
                if isinstance(result, dict)
                else {}
            )
            message = details.get("message", "Request failed.")
            code = details.get("code")

            raise InstagramAPIError(
                f"Instagram API request failed "
                f"(HTTP {response.status_code}, code={code}): {message}"
            )

        if not isinstance(result, dict):
            raise InstagramAPIError(
                "Instagram returned an unexpected response format."
            )

        return result

    def get_profile(self):
        """Retrieve the authorized account's basic profile information."""
        return self._request(
            "GET",
            self.user_id,
            params={"fields": "user_id,username"},
        )

    def create_image_container(self, image_url, caption):
        """
        Create an image-post container without publishing it.

        image_url must be an HTTPS URL that Instagram can access.
        A local Windows file path is not sufficient.
        """
        if not isinstance(image_url, str):
            raise ValueError("image_url must be a string.")

        image_url = image_url.strip()

        if not image_url.startswith("https://"):
            raise ValueError(
                "image_url must be a publicly accessible HTTPS URL."
            )

        if not isinstance(caption, str) or not caption.strip():
            raise ValueError("A non-empty caption is required.")

        result = self._request(
            "POST",
            f"{self.user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption.strip(),
            },
        )

        creation_id = result.get("id")

        if not creation_id:
            raise InstagramAPIError(
                "Instagram did not return a media container ID."
            )

        return creation_id
    
    def get_container_status(self, creation_id):
        """Check whether Instagram has finished processing a container."""
        if not isinstance(creation_id, str) or not creation_id.strip():
            raise ValueError("A valid creation_id is required.")

        return self._request(
            "GET",
            creation_id.strip(),
            params={"fields": "status_code,status"},
        )


    def publish_container(self, creation_id):
        """
        Publish a previously created media container.

        Call this only after explicit human approval and after checking
        that the container is ready for publishing.
        """
        if not isinstance(creation_id, str) or not creation_id.strip():
            raise ValueError("A valid creation_id is required.")

        result = self._request(
            "POST",
            f"{self.user_id}/media_publish",
            data={"creation_id": creation_id.strip()},
        )

        media_id = result.get("id")

        if not media_id:
            raise InstagramAPIError(
                "Instagram did not confirm a published media ID."
            )

        return media_id
