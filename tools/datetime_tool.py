from datetime import datetime

from tools.base import BaseTool


class DateTimeTool(BaseTool):
    """
    Local date and time tool.
    """

    name = "datetime"

    description = (
        "Get the current local date, time, day of the week, "
        "or full date and time from the computer."
    )

    def execute(self, mode="full"):
        """
        Return the requested local date/time information.
        """

        now = datetime.now()

        if mode == "date":
            return now.strftime("%Y-%m-%d")

        if mode == "time":
            return now.strftime("%H:%M:%S")

        if mode == "day":
            return now.strftime("%A")

        if mode == "full":
            return now.strftime(
                "%A, %d %B %Y, %H:%M:%S"
            )

        raise ValueError(
            "Invalid mode. Use: date, time, day, or full."
        )