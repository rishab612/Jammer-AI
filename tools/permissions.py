class ToolPermissionManager:

    def __init__(self):
        self.permissions = {
            "calculator": True,
            "datetime": True,
            "filesystem": True,
            "system_info": True,
            "python_exec": False,
        }

    def is_allowed(self, tool_name):
        return self.permissions.get(tool_name, False)

    def set_permission(self, tool_name, allowed):
        if tool_name not in self.permissions:
            raise ValueError(
                f"Unknown tool: {tool_name}"
            )

        if not isinstance(allowed, bool):
            raise TypeError(
                "Permission must be True or False."
            )

        self.permissions[tool_name] = allowed

    def get_permission(self, tool_name):
        if tool_name not in self.permissions:
            raise ValueError(
                f"Unknown tool: {tool_name}"
            )

        return self.permissions[tool_name]

    def list_permissions(self):
        return self.permissions.copy()