
from tools.selector import ToolSelector
from tools.executor import ToolExecutor
from tools.activity_logger import AgentActivityLogger


class JammerAgent:

    def __init__(
        self,
        registry,
        permission_manager=None,
        activity_logger=None
    ):
        self.registry = registry
        self.selector = ToolSelector(registry)
        self.executor = ToolExecutor(registry, permission_manager)

        self.activity_logger = (
            activity_logger or AgentActivityLogger()
        )

    def process(self, user_input):
        selection = self.selector.select(user_input)

        self.activity_logger.log(
            "tool_selection",
            input=self._safe_input(user_input),
            tool_name=getattr(selection, "tool_name", None),
            use_tool=getattr(selection, "use_tool", False),
            reason=getattr(selection, "reason", None),
        )

        execution = self.executor.execute(selection)

        self.activity_logger.log(
            "tool_execution",
            tool_name=execution.get("tool_name"),
            success=execution.get("success"),
            used_tool=execution.get("used_tool"),
            error=execution.get("error"),
        )

        return {
            "input": user_input,
            "selection": selection.to_dict(),
            "execution": execution
        }

    @staticmethod
    def _safe_input(user_input):
        """Limit the amount of user text stored in the activity log."""
        if not isinstance(user_input, str):
            return "<non-text input>"

        return user_input[:300] + (
            "... [truncated]" if len(user_input) > 300 else ""
        )
