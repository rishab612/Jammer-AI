
import unittest
from unittest.mock import Mock, patch

import check_agent_health


class TestHealthCLI(unittest.TestCase):

    @patch("check_agent_health.AgentHealthChecker")
    @patch("check_agent_health.JammerAgent")
    @patch("check_agent_health.ToolPermissionManager")
    @patch("check_agent_health.create_tool_registry")
    def test_healthy_components_return_zero(
        self,
        mock_registry,
        mock_permissions,
        mock_agent,
        mock_checker,
    ):
        permissions = mock_permissions.return_value
        permissions.is_allowed.return_value = False

        checker = mock_checker.return_value
        checker.print_report.return_value = {
            "healthy": True,
            "checks": {},
        }

        self.assertEqual(check_agent_health.main(), 0)
        mock_registry.assert_called_once()
        mock_agent.assert_called_once()
        checker.print_report.assert_called_once()

    @patch("check_agent_health.AgentHealthChecker")
    @patch("check_agent_health.JammerAgent")
    @patch("check_agent_health.ToolPermissionManager")
    @patch("check_agent_health.create_tool_registry")
    def test_unhealthy_agent_returns_one(
        self,
        mock_registry,
        mock_permissions,
        mock_agent,
        mock_checker,
    ):
        mock_permissions.return_value.is_allowed.return_value = False
        mock_checker.return_value.print_report.return_value = {
            "healthy": False,
            "checks": {},
        }

        self.assertEqual(check_agent_health.main(), 1)

    @patch("check_agent_health.create_tool_registry")
    def test_initialization_exception_returns_one(
        self,
        mock_registry,
    ):
        mock_registry.side_effect = RuntimeError("Initialization failed")

        self.assertEqual(check_agent_health.main(), 1)


if __name__ == "__main__":
    unittest.main()
