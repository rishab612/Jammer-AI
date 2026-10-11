from memory.database import get_connection


class MemoryManager:

    def add_memory(self, memory, category="general"):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO memories (memory, category)
            VALUES (?, ?)
            """,
            (memory, category)
        )

        connection.commit()
        connection.close()

    def get_all_memories(self):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, memory, category, created_at
            FROM memories
            ORDER BY id ASC
            """
        )

        memories = cursor.fetchall()

        connection.close()

        return memories

    def get_recent_memories(self, limit=20):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, memory, category, created_at
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        memories = cursor.fetchall()

        connection.close()

        return list(reversed(memories))

    def delete_memory(self, memory_id):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM memories WHERE id = ?",
            (memory_id,)
        )

        deleted = cursor.rowcount

        connection.commit()
        connection.close()

        return deleted > 0

    def clear_memories(self):

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("DELETE FROM memories")

        connection.commit()
        connection.close()

    def format_memories(self, limit=20):

        memories = self.get_recent_memories(limit)

        if not memories:
            return "No stored memories."

        lines = []

        for memory in memories:
            lines.append(
                f"[{memory['id']}] "
                f"{memory['memory']}"
            )

        return "\n".join(lines)