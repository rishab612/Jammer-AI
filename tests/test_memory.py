import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory.manager import MemoryManager


class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_jammer.db"
        self.connections = []

        def test_connection():
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            self.connections.append(connection)
            return connection

        self.patcher = patch(
            "memory.manager.get_connection",
            side_effect=test_connection
        )
        self.patcher.start()

        connection = test_connection()
        try:
            connection.execute("""
                CREATE TABLE memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        finally:
            connection.close()
            self.connections.remove(connection)

        self.manager = MemoryManager()

    def tearDown(self):
        self.patcher.stop()

        for connection in self.connections:
            try:
                connection.close()
            except sqlite3.Error:
                pass

        self.connections.clear()
        self.temp_dir.cleanup()

    def test_add_and_retrieve_memory(self):
        self.manager.add_memory("Learning Python", "education")
        memories = self.manager.get_all_memories()

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["memory"], "Learning Python")
        self.assertEqual(memories[0]["category"], "education")

    def test_default_category(self):
        self.manager.add_memory("Testing Jammer")
        memories = self.manager.get_all_memories()
        self.assertEqual(memories[0]["category"], "general")

    def test_recent_memories_respect_limit(self):
        self.manager.add_memory("Memory one")
        self.manager.add_memory("Memory two")
        self.manager.add_memory("Memory three")

        memories = self.manager.get_recent_memories(limit=2)

        self.assertEqual(len(memories), 2)
        self.assertEqual(memories[0]["memory"], "Memory two")
        self.assertEqual(memories[1]["memory"], "Memory three")

    def test_delete_existing_memory(self):
        self.manager.add_memory("Temporary memory")
        memory_id = self.manager.get_all_memories()[0]["id"]

        self.assertTrue(self.manager.delete_memory(memory_id))
        self.assertEqual(self.manager.get_all_memories(), [])

    def test_delete_missing_memory(self):
        self.assertFalse(self.manager.delete_memory(999999))

    def test_clear_memories(self):
        self.manager.add_memory("Memory one")
        self.manager.add_memory("Memory two")
        self.manager.clear_memories()

        self.assertEqual(self.manager.get_all_memories(), [])

    def test_format_memories(self):
        self.manager.add_memory("Prefers Python", "preferences")
        formatted = self.manager.format_memories()

        self.assertIn("Prefers Python", formatted)

    def test_format_empty_memories(self):
        self.assertEqual(
            self.manager.format_memories(),
            "No stored memories."
        )


if __name__ == "__main__":
    unittest.main()
