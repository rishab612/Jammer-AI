import unittest
from unittest.mock import MagicMock

from tools.executor import ToolExecutor
from tools.selector import ToolSelection
from tools.permissions import ToolPermissionManager


class TestToolExecutor(unittest.TestCase):

    def setUp(self):
        self.registry = MagicMock()
        self.registry.has.return_value = True

        self.permissions = ToolPermissionManager()
        self.executor = ToolExecutor(
            self.registry,
            self.permissions,
        )

    def make_selection(self, use_tool=True, tool_name="calculator", arguments=None):
        return ToolSelection(
            use_tool=use_tool,
            tool_name=tool_name,
            arguments=arguments or {},
        )

    def test_disabled_python_tool_is_blocked(self):
        selection = self.make_selection(
            tool_name="python_exec",
            arguments={"code": "print('SHOULD_NOT_RUN')"},
        )

        result = self.executor.execute(selection)

        self.assertFalse(result["success"])
        self.assertTrue(result["used_tool"])
        self.assertEqual(result["tool_name"], "python_exec")
        self.assertIn("Permission denied", result["error"])
        self.registry.execute.assert_not_called()

    def test_allowed_tool_executes(self):
        self.registry.execute.return_value = 42
        selection = self.make_selection(
            tool_name="calculator",
            arguments={"expression": "6 * 7"},
        )

        result = self.executor.execute(selection)

        self.assertTrue(result["success"])
        self.assertTrue(result["used_tool"])
        self.assertEqual(result["result"], 42)
        self.registry.execute.assert_called_once_with(
            "calculator",
            expression="6 * 7",
        )

    def test_disabled_tool_never_reaches_registry(self):
        self.permissions.set_permission("calculator", False)
        selection = self.make_selection(
            tool_name="calculator",
            arguments={"expression": "1 + 1"},
        )

        result = self.executor.execute(selection)

        self.assertFalse(result["success"])
        self.assertIn("Permission denied", result["error"])
        self.registry.execute.assert_not_called()

    def test_unregistered_tool_is_not_executed(self):
        self.registry.has.return_value = False
        selection = self.make_selection(tool_name="unknown_tool")

        result = self.executor.execute(selection)

        self.assertFalse(result["success"])
        self.assertIn("not registered", result["error"])
        self.registry.execute.assert_not_called()

    def test_no_tool_selection_does_not_execute(self):
        selection = self.make_selection(
            use_tool=False,
            tool_name=None,
        )

        result = self.executor.execute(selection)

        self.assertTrue(result["success"])
        self.assertFalse(result["used_tool"])
        self.assertIsNone(result["result"])
        self.registry.execute.assert_not_called()

    def test_missing_tool_name_is_rejected(self):
        selection = self.make_selection(tool_name=None)

        result = self.executor.execute(selection)

        self.assertFalse(result["success"])
        self.assertIn("missing", result["error"])
        self.registry.execute.assert_not_called()

    def test_invalid_selection_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.executor.execute({"use_tool": False})

    def test_tool_exception_is_returned_as_error(self):
        self.registry.execute.side_effect = RuntimeError("test failure")
        selection = self.make_selection(
            tool_name="calculator",
            arguments={"expression": "1 + 1"},
        )

        result = self.executor.execute(selection)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "test failure")
        self.assertIsNone(result["result"])


if __name__ == "__main__":
    unittest.main()
