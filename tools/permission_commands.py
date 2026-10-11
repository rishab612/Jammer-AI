from tools.permissions import ToolPermissionManager


class PermissionCommands:

    def __init__(self, permission_manager):
        self.permission_manager = permission_manager

    def status(self):
        return self.permission_manager.list_permissions()

    def enable(self, tool_name):
        self.permission_manager.set_permission(
            tool_name,
            True
        )

        return {
            "success": True,
            "tool": tool_name,
            "allowed": True
        }

    def disable(self, tool_name):
        self.permission_manager.set_permission(
            tool_name,
            False
        )

        return {
            "success": True,
            "tool": tool_name,
            "allowed": False
        }