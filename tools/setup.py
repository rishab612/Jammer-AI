from tools.registry import ToolRegistry
from tools.calculator import CalculatorTool
from tools.datetime_tool import DateTimeTool
from tools.filesystem import FileSystemTool
from tools.system_info import SystemInfoTool
from tools.python_exec import PythonExecutionTool


def create_tool_registry():
    registry = ToolRegistry()

    registry.register(
        CalculatorTool()
    )

    registry.register(
        DateTimeTool()
    )

    registry.register(
        FileSystemTool()
    )

    registry.register(
        SystemInfoTool()
    )

    registry.register(
        PythonExecutionTool()
    )

    return registry