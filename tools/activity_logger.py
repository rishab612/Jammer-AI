
import json
from datetime import datetime
from pathlib import Path


class AgentActivityLogger:
    """Append structured activity records to a local JSONL file."""

    def __init__(self, log_path=None):
        project_root = Path(__file__).resolve().parent.parent

        self.log_path = (
            Path(log_path)
            if log_path
            else project_root / "logs" / "agent_activity.jsonl"
        )

        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    @staticmethod
    def _sanitize(value, limit=1000):
        """Preserve JSON types while limiting logged text."""

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):
            if len(value) > limit:
                return value[:limit] + "... [truncated]"
            return value

        # Avoid accidentally logging arbitrary object contents.
        return f"<{type(value).__name__}>"

    def log(self, event, **details):
        """Append one record; logging failures must not stop Jammer."""

        record = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "event": self._sanitize(event, 100),
        }

        for key, value in details.items():
            safe_key = self._sanitize(key, 100)
            record[safe_key] = self._sanitize(value)

        try:
            with self.log_path.open(
                "a",
                encoding="utf-8"
            ) as file:
                file.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

        except OSError as error:
            print(f"\nActivity logging warning: {error}")
