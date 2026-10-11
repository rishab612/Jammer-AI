import platform
import socket
import sys

import psutil

from tools.base import BaseTool


class SystemInfoTool(BaseTool):
    """
    Read-only system information tool.
    """

    name = "system_info"

    description = (
        "Get basic information about the local computer, "
        "including operating system, CPU, RAM, Python version, "
        "architecture, and hostname."
    )

    def execute(self, category="all"):
        """
        Return requested system information.
        """

        category = category.lower().strip()

        if category == "os":
            return self._get_os_info()

        if category == "cpu":
            return self._get_cpu_info()

        if category == "memory":
            return self._get_memory_info()

        if category == "python":
            return self._get_python_info()

        if category == "all":
            return self._get_all_info()

        raise ValueError(
            "Invalid category. Use: os, cpu, memory, python, or all."
        )

    def _get_os_info(self):

        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0]
        }

    def _get_cpu_info(self):

        return {
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "usage_percent": psutil.cpu_percent(interval=0.5)
        }

    def _get_memory_info(self):

        memory = psutil.virtual_memory()

        return {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "used_gb": round(memory.used / (1024 ** 3), 2),
            "usage_percent": memory.percent
        }

    def _get_python_info(self):

        return {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable
        }

    def _get_all_info(self):

        return {
            "os": self._get_os_info(),
            "cpu": self._get_cpu_info(),
            "memory": self._get_memory_info(),
            "python": self._get_python_info(),
            "hostname": socket.gethostname()
        }