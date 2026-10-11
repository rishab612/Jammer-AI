import unittest
from tools.registry import ToolRegistry
from tools.selector import ToolSelector


class TestToolSelector(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        self.selector = ToolSelector(self.registry)

    def test_calculation_routes_to_calculator(self):
        result = self.selector.select("What is 125 * 48?")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.tool_name, "calculator")
        self.assertEqual(result.arguments["expression"], "125 * 48")

    def test_cpu_question_routes_to_system_info(self):
        result = self.selector.select("What is my CPU usage?")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.tool_name, "system_info")
        self.assertEqual(result.arguments["category"], "cpu")

    def test_file_existence_routes_to_filesystem(self):
        result = self.selector.select(
            r"Does C:\AI\Jammer\main.py exist?"
        )
        self.assertTrue(result.use_tool)
        self.assertEqual(result.tool_name, "filesystem")
        self.assertEqual(result.arguments["action"], "exists")
        self.assertEqual(
            result.arguments["path"],
            r"C:\AI\Jammer\main.py"
        )

    def test_list_files_routes_to_filesystem(self):
        result = self.selector.select("List files in rag")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.tool_name, "filesystem")
        self.assertEqual(result.arguments["action"], "list")
        self.assertEqual(result.arguments["path"], "rag")

    def test_terminal_command_is_not_selected_as_tool(self):
        result = self.selector.select(
            r"Get-Content logs\agent_activity.jsonl -Tail 15"
        )
        self.assertFalse(result.use_tool)

    def test_general_question_does_not_force_tool(self):
        result = self.selector.select(
            "Explain why the sky appears blue"
        )
        self.assertFalse(result.use_tool)


    def test_terminal_command_guard_blocks_launch_patterns(self):
        commands = [
            "& python script.py",
            "Start-Process powershell",
            "Invoke-Expression $command",
            "Invoke-Command -ScriptBlock { Get-Date }",
            "Start-Job { python script.py }",
            "schtasks /query",
            "sc.exe query",
        ]

        for command in commands:
            with self.subTest(command=command):
                result = self.selector.select(command)
                self.assertFalse(result.use_tool)
                self.assertIn("terminal command", result.reason.lower())

    def test_terminal_command_guard_does_not_block_normal_questions(self):
        questions = [
            "Explain what PowerShell is",
            "How does Python work?",
            "What is Git used for?",
        ]

        for question in questions:
            with self.subTest(question=question):
                result = self.selector.select(question)
                self.assertFalse(result.use_tool)
                self.assertIn("No available tool", result.reason)

    
    def test_natural_language_multiplication(self):
        result = self.selector.select("Multiply 5 by 4")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.tool_name, "calculator")
        self.assertEqual(result.arguments["expression"], "5 * 4")

    def test_natural_language_addition(self):
        result = self.selector.select("Add 5 and 3")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.arguments["expression"], "5 + 3")

    def test_natural_language_subtraction_order(self):
        result = self.selector.select("Subtract 70 from 150")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.arguments["expression"], "150 - 70")

    def test_unicode_multiplication_symbol(self):
        result = self.selector.select("What is 5 × 4?")
        self.assertTrue(result.use_tool)
        self.assertEqual(result.arguments["expression"], "5 * 4")

    
    def test_empty_input_is_not_routed(self):
        result = self.selector.select("")
        self.assertFalse(result.use_tool)
        self.assertEqual(result.reason, "Empty user request.")

    def test_whitespace_input_is_not_routed(self):
        result = self.selector.select("   ")
        self.assertFalse(result.use_tool)
        self.assertEqual(result.reason, "Empty user request.")

    def test_non_string_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.selector.select(None)

    def test_ambiguous_arithmetic_is_not_routed(self):
        result = self.selector.select(
            "I am learning mathematics and Python"
        )
        self.assertFalse(result.use_tool)


if __name__ == "__main__":
    unittest.main()
