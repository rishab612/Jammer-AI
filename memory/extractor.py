import re


class MemoryExtractor:

    def detect(self, text):

        text = text.strip()

        patterns = [

            # Name
            (
                r"^(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z .'-]{1,50})[.!]?$",
                "personal",
                "The user's name is {0}."
            ),

            # Degree / education
            (
                r"^(?:i study|i am studying)\s+(.+?)[.!]?$",
                "education",
                "The user studies {0}."
            ),

            (
                r"^(?:my degree is|i have a degree in)\s+(.+?)[.!]?$",
                "education",
                "The user's degree is {0}."
            ),

            # Favorites
            (
                r"^my favorite (.+?) is (.+?)[.!]?$",
                "preference",
                "The user's favorite {0} is {1}."
            ),

            # Likes
            (
                r"^i like (.+?)[.!]?$",
                "preference",
                "The user likes {0}."
            ),

            # Dislikes
            (
                r"^i (?:don't|do not) like (.+?)[.!]?$",
                "preference",
                "The user does not like {0}."
            ),

            # Preferences
            (
                r"^i prefer (.+?)[.!]?$",
                "preference",
                "The user prefers {0}."
            ),

            # Location
            (
                r"^(?:i live in|i am from|i'm from)\s+(.+?)[.!]?$",
                "location",
                "The user is from/lives in {0}."
            ),
        ]

        for pattern, category, template in patterns:

            match = re.match(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                groups = match.groups()

                try:
                    memory = template.format(*groups)
                except IndexError:
                    continue

                return {
                    "memory": memory,
                    "category": category
                }

        return None