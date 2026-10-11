
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tools.health import AgentHealthChecker


class TestAgentHealthChecker(unittest.TestCase):

    def make_agent(self):
        tools = [
            SimpleNamespace(name="calculator"),
            SimpleNamespace(name="datetime"),
            SimpleNamespace(name="filesystem"),
            SimpleNamespace(name="system_info"),
        ]

        registry = Mock()
        registry.list_tools.return_value = tools
        registry.has.return_value = True

        permission_manager = Mock()
        permission_manager.is_allowed.return_value = True

        executor = Mock()
        executor.permission_manager = permission_manager

        logger = Mock()

        agent = SimpleNamespace(
            process=Mock(),
            registry=registry,
            executor=executor,
            activity_logger=logger,
        )

        return agent

    def test_healthy_agent(self):
        checker = AgentHealthChecker(self.make_agent())

        report = checker.check()

        self.assertTrue(report["healthy"])
        self.assertTrue(
            all(item["healthy"] for item in report["checks"].values())
        )

    def test_missing_required_tool(self):
        agent = self.make_agent()
        agent.registry.list_tools.return_value = [
            SimpleNamespace(name="calculator"),
        ]

        report = AgentHealthChecker(agent).check()

        self.assertFalse(report["healthy"])
        self.assertFalse(report["checks"]["registry"]["healthy"])

    def test_missing_executor_interface(self):
        agent = self.make_agent()
        agent.executor.execute = None

        report = AgentHealthChecker(agent).check()

        self.assertFalse(report["healthy"])
        self.assertFalse(report["checks"]["executor"]["healthy"])

    def test_missing_permission_interface(self):
        agent = self.make_agent()
        agent.executor.permission_manager.is_allowed = None

        report = AgentHealthChecker(agent).check()

        self.assertFalse(report["healthy"])
        self.assertFalse(report["checks"]["permissions"]["healthy"])

    def test_missing_activity_logger(self):
        agent = self.make_agent()
        agent.activity_logger = None

        report = AgentHealthChecker(agent).check()

        self.assertFalse(report["healthy"])
        self.assertFalse(
            report["checks"]["activity_logger"]["healthy"]
        )

    def test_missing_agent_process(self):
        agent = self.make_agent()
        agent.process = None

        report = AgentHealthChecker(agent).check()

        self.assertFalse(report["healthy"])
        self.assertFalse(report["checks"]["agent"]["healthy"])

    def test_registry_exception_is_reported(self):
        agent = self.make_agent()
        agent.registry.list_tools.side_effect = RuntimeError(
            "Registry unavailable"
        )

        report = AgentHealthChecker(agent).check()

        self.assertFalse(report["healthy"])
        self.assertFalse(report["checks"]["registry"]["healthy"])
        self.assertIn(
            "Registry check failed",
            report["checks"]["registry"]["details"],
        )


if __name__ == "__main__":
    unittest.main()
