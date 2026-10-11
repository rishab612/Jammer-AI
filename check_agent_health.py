
import sys

from tools.setup import create_tool_registry
from tools.permissions import ToolPermissionManager
from tools.agent import JammerAgent
from tools.health import AgentHealthChecker


def main():
    print("Initializing Jammer agent components...")

    try:
        registry = create_tool_registry()
        permissions = ToolPermissionManager()

        agent = JammerAgent(
            registry=registry,
            permission_manager=permissions,
        )

        checker = AgentHealthChecker(agent)
        report = checker.print_report()

        # Verify that Python execution remains disabled.
        python_exec_disabled = not permissions.is_allowed(
            "python_exec"
        )

        print(
            "Python execution disabled: "
            + ("YES" if python_exec_disabled else "NO")
        )

        if not python_exec_disabled:
            print(
                "WARNING: Python execution is enabled. "
                "Review your permission configuration."
            )

        return 0 if report["healthy"] and python_exec_disabled else 1

    except Exception as error:
        print(f"HEALTH CHECK ERROR: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
