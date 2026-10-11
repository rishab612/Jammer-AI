import unittest

from tools.permissions import ToolPermissionManager
from tools.permission_commands import PermissionCommands


class TestToolPermissions(unittest.TestCase):

    def setUp(self):
        self.manager = ToolPermissionManager()
        self.commands = PermissionCommands(self.manager)

    def test_python_execution_disabled_by_default(self):
        self.assertFalse(self.manager.is_allowed("python_exec"))

    def test_standard_tools_allowed_by_default(self):
        for tool in ["calculator", "datetime", "filesystem", "system_info"]:
            with self.subTest(tool=tool):
                self.assertTrue(self.manager.is_allowed(tool))

    def test_disable_tool(self):
        self.manager.set_permission("calculator", False)
        self.assertFalse(self.manager.is_allowed("calculator"))

    def test_enable_tool(self):
        self.manager.set_permission("python_exec", True)
        self.assertTrue(self.manager.is_allowed("python_exec"))

    def test_unknown_tool_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.set_permission("unknown_tool", True)

    def test_non_boolean_permission_rejected(self):
        with self.assertRaises(TypeError):
            self.manager.set_permission("calculator", "yes")

    def test_permission_commands(self):
        result = self.commands.disable("calculator")
        self.assertEqual(
            result,
            {"success": True, "tool": "calculator", "allowed": False}
        )

        result = self.commands.enable("calculator")
        self.assertEqual(
            result,
            {"success": True, "tool": "calculator", "allowed": True}
        )

    def test_permission_status_returns_copy(self):
        status = self.commands.status()
        status["python_exec"] = True

        self.assertFalse(self.manager.is_allowed("python_exec"))


if __name__ == "__main__":
    unittest.main()
