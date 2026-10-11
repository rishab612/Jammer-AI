import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.activity_logger import AgentActivityLogger


class TestActivityLogger(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.temp_dir.name) / "activity.jsonl"
        self.logger = AgentActivityLogger(self.log_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_log_creates_valid_json_record(self):
        self.logger.log("test_event", message="hello")

        records = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(records), 1)

        record = json.loads(records[0])
        self.assertEqual(record["event"], "test_event")
        self.assertEqual(record["message"], "hello")
        self.assertIn("timestamp", record)

    def test_multiple_events_append(self):
        self.logger.log("first_event")
        self.logger.log("second_event")

        records = [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
        ]

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["event"], "first_event")
        self.assertEqual(records[1]["event"], "second_event")

    def test_sanitization_preserves_json_types(self):
        self.logger.log(
            "typed_event",
            enabled=True,
            count=5,
            missing=None,
            object_value=object()
        )

        record = json.loads(self.log_path.read_text(encoding="utf-8"))

        self.assertIs(record["enabled"], True)
        self.assertEqual(record["count"], 5)
        self.assertIsNone(record["missing"])
        self.assertEqual(record["object_value"], "<object>")

    def test_long_text_is_truncated(self):
        self.logger.log("long_event", message="x" * 1500)

        record = json.loads(self.log_path.read_text(encoding="utf-8"))
        self.assertLess(len(record["message"]), 1100)
        self.assertTrue(record["message"].endswith("... [truncated]"))

    def test_write_failure_does_not_raise(self):
        with patch.object(
            Path,
            "open",
            side_effect=OSError("simulated disk error")
        ):
            # The logger should handle the write failure.
            self.logger.log("failure_test")


if __name__ == "__main__":
    unittest.main()
