from tools.selector import ToolSelection
from tools.permissions import ToolPermissionManager


class ToolExecutor:

    def __init__(self, registry, permission_manager=None):
        self.registry = registry

        if permission_manager is None:
            permission_manager = ToolPermissionManager()

        self.permission_manager = permission_manager

    def execute(self, selection: ToolSelection):

        if not isinstance(selection, ToolSelection):
            raise TypeError(
                "Expected a ToolSelection object."
            )

        # No tool required
        if not selection.use_tool:
            return {
                "success": True,
                "used_tool": False,
                "tool_name": None,
                "result": None,
                "error": None
            }

        # Tool name missing
        if not selection.tool_name:
            return {
                "success": False,
                "used_tool": True,
                "tool_name": None,
                "result": None,
                "error": "Tool name is missing."
            }

        # Tool does not exist
        if not self.registry.has(selection.tool_name):
            return {
                "success": False,
                "used_tool": True,
                "tool_name": selection.tool_name,
                "result": None,
                "error": (
                    f"Tool '{selection.tool_name}' "
                    "is not registered."
                )
            }

        # Permission check
        if not self.permission_manager.is_allowed(
            selection.tool_name
        ):
            return {
                "success": False,
                "used_tool": True,
                "tool_name": selection.tool_name,
                "result": None,
                "error": (
                    f"Permission denied for tool "
                    f"'{selection.tool_name}'."
                )
            }

        # Execute tool
        try:
            result = self.registry.execute(
                selection.tool_name,
                **selection.arguments
            )

            return {
                "success": True,
                "used_tool": True,
                "tool_name": selection.tool_name,
                "result": result,
                "error": None
            }

        except Exception as error:
            return {
                "success": False,
                "used_tool": True,
                "tool_name": selection.tool_name,
                "result": None,
                "error": str(error)
            }