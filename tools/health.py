
class AgentHealthChecker:
    """Check Jammer agent component wiring and basic interfaces."""

    REQUIRED_TOOLS = {
        "calculator",
        "datetime",
        "filesystem",
        "system_info",
    }

    def __init__(self, agent):
        self.agent = agent

    def check(self):
        checks = {}

        # 1. Agent
        checks["agent"] = {
            "healthy": callable(getattr(self.agent, "process", None)),
            "details": "process() interface available"
            if callable(getattr(self.agent, "process", None))
            else "process() interface missing",
        }

        # 2. Registry
        registry = getattr(self.agent, "registry", None)

        try:
            registered = {
                tool.name for tool in registry.list_tools()
            }
            missing = sorted(self.REQUIRED_TOOLS - registered)

            registry_ok = (
                callable(getattr(registry, "list_tools", None))
                and callable(getattr(registry, "has", None))
                and not missing
            )

            checks["registry"] = {
                "healthy": registry_ok,
                "details": (
                    f"{len(registered)} tools registered"
                    if registry_ok
                    else f"Missing required tools: {missing}"
                ),
            }
        except Exception as error:
            checks["registry"] = {
                "healthy": False,
                "details": f"Registry check failed: {error}",
            }

        # 3. Executor and permission manager
        executor = getattr(self.agent, "executor", None)
        permission_manager = getattr(
            executor, "permission_manager", None
        )

        executor_ok = callable(
            getattr(executor, "execute", None)
        )
        permission_ok = callable(
            getattr(permission_manager, "is_allowed", None)
        )

        checks["executor"] = {
            "healthy": executor_ok,
            "details": "execute() interface available"
            if executor_ok
            else "Executor interface missing",
        }

        checks["permissions"] = {
            "healthy": permission_ok,
            "details": "is_allowed() interface available"
            if permission_ok
            else "Permission manager interface missing",
        }

        # 4. Activity logger
        logger = getattr(self.agent, "activity_logger", None)
        logger_ok = callable(getattr(logger, "log", None))

        checks["activity_logger"] = {
            "healthy": logger_ok,
            "details": "log() interface available"
            if logger_ok
            else "Activity logger interface missing",
        }

        return {
            "healthy": all(
                item["healthy"] for item in checks.values()
            ),
            "checks": checks,
        }

    def print_report(self):
        report = self.check()

        print("=" * 55)
        print("JAMMER AI - AGENT HEALTH")
        print("=" * 55)

        for name, item in report["checks"].items():
            status = "OK" if item["healthy"] else "FAIL"
            print(
                f"{name.replace('_', ' ').title():20} "
                f"{status:5} {item['details']}"
            )

        print("-" * 55)
        print(
            "Overall: " +
            ("HEALTHY" if report["healthy"] else "UNHEALTHY")
        )

        return report
