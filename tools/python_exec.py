import subprocess
import sys

from tools.base import BaseTool


class PythonExecutionTool(BaseTool):
    """
    Controlled local Python execution tool.
    """

    name = "python_exec"

    description = (
        "Execute Python code locally and return its output. "
        "Useful for calculations, data processing, and Python tasks."
    )

    DEFAULT_TIMEOUT = 10
    MAX_TIMEOUT = 30
    MAX_OUTPUT = 10000

    def execute(self, code, timeout=DEFAULT_TIMEOUT):
        """
        Execute Python code in a separate subprocess.
        """

        if not isinstance(code, str):
            raise TypeError("Python code must be a string.")

        code = code.strip()

        if not code:
            raise ValueError("Python code cannot be empty.")

        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            raise ValueError("Timeout must be an integer.")

        timeout = max(1, min(timeout, self.MAX_TIMEOUT))

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "timeout": True,
                "stdout": "",
                "stderr": (
                    f"Execution exceeded the {timeout}-second timeout."
                ),
                "return_code": None
            }

        stdout = result.stdout[:self.MAX_OUTPUT]
        stderr = result.stderr[:self.MAX_OUTPUT]

        return {
            "success": result.returncode == 0,
            "timeout": False,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": result.returncode
        }