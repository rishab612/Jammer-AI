import unittest
from unittest.mock import Mock
from core.chat import JammerChat


class FakeModel:
    def __init__(self, response="Hello from Jammer!"):
        self.response = response
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class TestJammerChat(unittest.TestCase):

    def setUp(self):
        self.model = FakeModel()
        self.memory = Mock()
        self.memory.format_memories.return_value = "No stored memories."
        self.chat = JammerChat(
            model=self.model,
            memory_manager=self.memory
        )
        # Avoid writing to the real activity log during tests.
        self.chat.activity_logger = Mock()

    def test_normal_response(self):
        response = self.chat.send("Hello")
        self.assertEqual(response, "Hello from Jammer!")

    def test_conversation_history_is_saved(self):
        self.chat.send("First message")
        self.chat.send("Second message")

        self.assertEqual(len(self.chat.history), 4)
        self.assertEqual(self.chat.history[0]["role"], "user")
        self.assertEqual(self.chat.history[1]["role"], "assistant")
        self.assertEqual(
            self.chat.history[0]["content"], "First message"
        )
        self.assertEqual(
            self.chat.history[2]["content"], "Second message"
        )

    def test_previous_history_is_sent_to_model(self):
        self.chat.send("First message")
        self.chat.send("Second message")

        second_call_messages = self.model.calls[1]
        self.assertTrue(
            any(
                message.get("content") == "First message"
                for message in second_call_messages
            )
        )

    def test_long_input_does_not_crash(self):
        long_message = "testing " * 3000
        response = self.chat.send(long_message)

        self.assertEqual(response, "Hello from Jammer!")
        self.assertEqual(self.chat.history[0]["content"], long_message)

    def test_clear_history(self):
        self.chat.send("Remember this conversation")
        self.chat.clear()

        self.assertEqual(self.chat.history, [])

    def test_model_failure_is_logged_and_raised(self):
        self.model.response = RuntimeError("Simulated model failure")

        with self.assertRaisesRegex(
            RuntimeError, "Simulated model failure"
        ):
            self.chat.send("Trigger failure")

        self.assertEqual(self.chat.history, [])

        logged_events = [
            call.args[0]
            for call in self.chat.activity_logger.log.call_args_list
        ]

        self.assertIn("model_generation", logged_events)
        self.assertIn("chat_request_finished", logged_events)

        failed_generation = [
            call for call in self.chat.activity_logger.log.call_args_list
            if call.args and call.args[0] == "model_generation"
        ]

        self.assertTrue(
            any(call.kwargs.get("success") is False
                for call in failed_generation)
        )

    def test_non_text_model_response_is_rejected(self):
        self.model.response = None

        with self.assertRaisesRegex(
            TypeError, "non-text response"
        ):
            self.chat.send("Trigger invalid response")

        self.assertEqual(self.chat.history, [])

    
    def test_terminal_command_is_not_executed(self):
        from unittest.mock import Mock
        from tools.selector import ToolSelection

        selector = Mock()
        selector.select.return_value = ToolSelection(
            use_tool=False,
            tool_name=None,
            arguments={},
            reason="The input appears to be a terminal command.",
        )

        executor = Mock()
        agent = Mock()
        agent.selector = selector
        agent.executor = executor
        agent.activity_logger = Mock()

        model = FakeModel("I cannot execute terminal commands.")
        chat = JammerChat(
            model=model,
            memory_manager=self.memory,
            agent=agent,
        )
        chat.activity_logger = Mock()

        response = chat.send("python script.py")

        executor.execute.assert_not_called()
        self.assertEqual(
            response,
            "I cannot execute terminal commands.",
        )

        messages = model.calls[0]
        safety_messages = [
            message["content"]
            for message in messages
            if message.get("role") == "system"
            and "TERMINAL COMMAND SAFETY NOTICE" in
            message.get("content", "")
        ]

        self.assertEqual(len(safety_messages), 1)
        self.assertIn("has not executed it", safety_messages[0])

    def test_normal_chat_does_not_receive_terminal_notice(self):
        response = self.chat.send("Explain what Python is.")

        self.assertEqual(response, "Hello from Jammer!")

        messages = self.model.calls[0]
        self.assertFalse(
            any(
                message.get("role") == "system"
                and "TERMINAL COMMAND SAFETY NOTICE" in
                message.get("content", "")
                for message in messages
            )
        )



if __name__ == "__main__":
    unittest.main()
