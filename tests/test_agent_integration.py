import unittest
from unittest.mock import Mock

from core.chat import JammerChat
from tools.agent import JammerAgent
from tools.permissions import ToolPermissionManager
from tools.selector import ToolSelection


class FakeModel:
    def __init__(self, response="Jammer response"):
        self.response = response
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return self.response


class TestAgentIntegration(unittest.TestCase):

    def setUp(self):
        self.registry = Mock()
        self.registry.has.return_value = True
        self.registry.execute.return_value = 6000

        self.permissions = ToolPermissionManager()
        self.logger = Mock()

        self.agent = JammerAgent(
            registry=self.registry,
            permission_manager=self.permissions,
            activity_logger=self.logger,
        )

    def selection(self, tool_name, arguments=None):
        return ToolSelection(
            use_tool=True,
            tool_name=tool_name,
            arguments=arguments or {},
            reason="Integration test",
        )

    def test_agent_executes_permitted_calculator_tool(self):
        self.agent.selector.select = Mock(
            return_value=self.selection(
                "calculator",
                {"expression": "125 * 48"},
            )
        )

        result = self.agent.process("Calculate 125 * 48")

        self.assertTrue(result["execution"]["success"])
        self.assertEqual(result["execution"]["result"], 6000)
        self.registry.execute.assert_called_once_with(
            "calculator",
            expression="125 * 48",
        )

    def test_agent_blocks_disabled_python_execution(self):
        self.agent.selector.select = Mock(
            return_value=self.selection(
                "python_exec",
                {"code": "print('SHOULD_NOT_RUN')"},
            )
        )

        result = self.agent.process("Run a Python script")

        self.assertFalse(result["execution"]["success"])
        self.assertIn(
            "Permission denied",
            result["execution"]["error"],
        )
        self.registry.execute.assert_not_called()

    def test_agent_logs_selection_and_execution(self):
        self.agent.selector.select = Mock(
            return_value=self.selection(
                "calculator",
                {"expression": "125 * 48"},
            )
        )

        self.agent.process("Calculate 125 * 48")

        events = [
            call.args[0]
            for call in self.logger.log.call_args_list
        ]

        self.assertIn("tool_selection", events)
        self.assertIn("tool_execution", events)

    def test_chat_passes_tool_result_to_model(self):
        self.agent.selector.select = Mock(
            return_value=self.selection(
                "calculator",
                {"expression": "125 * 48"},
            )
        )

        model = FakeModel("The answer is 6000.")
        memory = Mock()
        memory.format_memories.return_value = ""

        chat = JammerChat(
            model=model,
            memory_manager=memory,
            agent=self.agent,
        )

        response = chat.send("Calculate 125 * 48")

        self.assertEqual(response, "The answer is 6000.")
        self.assertEqual(len(model.calls), 1)

        messages = model.calls[0]
        tool_messages = [
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
            and "Tool Result:" in message.get("content", "")
        ]

        self.assertEqual(len(tool_messages), 1)
        self.assertIn("6000", tool_messages[0])

    def test_chat_reports_denied_tool_to_model(self):
        self.agent.selector.select = Mock(
            return_value=self.selection(
                "python_exec",
                {"code": "print('SHOULD_NOT_RUN')"},
            )
        )

        model = FakeModel("Python execution is disabled.")
        memory = Mock()
        memory.format_memories.return_value = ""

        chat = JammerChat(
            model=model,
            memory_manager=memory,
            agent=self.agent,
        )

        response = chat.send("Run Python code")

        self.assertEqual(
            response,
            "Python execution is disabled.",
        )
        self.registry.execute.assert_not_called()

        messages = model.calls[0]
        error_messages = [
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
            and "Tool error:" in message.get("content", "")
        ]

        self.assertEqual(len(error_messages), 1)
        self.assertIn("Permission denied", error_messages[0])

    def test_chat_handles_normal_message_without_tool(self):
        self.agent.selector.select = Mock(
            return_value=ToolSelection(
                use_tool=False,
                tool_name=None,
                arguments={},
                reason="General conversation",
            )
        )

        model = FakeModel("Hello from Jammer!")
        memory = Mock()
        memory.format_memories.return_value = ""

        chat = JammerChat(
            model=model,
            memory_manager=memory,
            agent=self.agent,
        )

        response = chat.send("Hello")

        self.assertEqual(response, "Hello from Jammer!")
        self.registry.execute.assert_not_called()

    
    def test_chat_reports_tool_execution_exception(self):
        self.agent.selector.select = Mock(
            return_value=self.selection(
                "calculator",
                {"expression": "1 + 1"},
            )
        )
        self.registry.execute.side_effect = RuntimeError(
            "Simulated calculator failure"
        )

        model = FakeModel("The calculator tool failed.")
        memory = Mock()
        memory.format_memories.return_value = ""

        chat = JammerChat(
            model=model,
            memory_manager=memory,
            agent=self.agent,
        )

        response = chat.send("Calculate 1 + 1")

        self.assertEqual(response, "The calculator tool failed.")
        self.registry.execute.assert_called_once()

        messages = model.calls[0]
        error_messages = [
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
            and "Tool error:" in message.get("content", "")
        ]

        self.assertEqual(len(error_messages), 1)
        self.assertIn(
            "Simulated calculator failure",
            error_messages[0],
        )

    def test_chat_handles_selector_exception(self):
        self.agent.selector.select = Mock(
            side_effect=RuntimeError("Selector failure")
        )

        model = FakeModel("I can still respond.")
        memory = Mock()
        memory.format_memories.return_value = ""

        chat = JammerChat(
            model=model,
            memory_manager=memory,
            agent=self.agent,
        )

        response = chat.send("Hello")

        self.assertEqual(response, "I can still respond.")
        self.assertEqual(len(model.calls), 1)
        self.registry.execute.assert_not_called()

        events = [
            call.args[0]
            for call in chat.activity_logger.log.call_args_list
        ]
        self.assertIn("tool_selection_error", events)

    def test_terminal_command_guard_prevents_tool_execution(self):
        # Use the real selector to test the actual routing guard.
        model = FakeModel("I cannot execute terminal commands.")
        memory = Mock()
        memory.format_memories.return_value = ""

        chat = JammerChat(
            model=model,
            memory_manager=memory,
            agent=self.agent,
        )
        chat.activity_logger = Mock()

        response = chat.send("python script.py")

        self.assertEqual(
            response,
            "I cannot execute terminal commands.",
        )
        self.registry.execute.assert_not_called()

        messages = model.calls[0]
        self.assertTrue(
            any(
                message.get("role") == "system"
                and "TERMINAL COMMAND SAFETY NOTICE"
                in message.get("content", "")
                for message in messages
            )
        )



if __name__ == "__main__":
    unittest.main()
