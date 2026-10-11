class ToolRegistry:

    def __init__(self):
        self.tools = {}

    def register(self, tool):
        if tool.name in self.tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered."
            )

        self.tools[tool.name] = tool

    def unregister(self, name):
        if name in self.tools:
            del self.tools[name]

    def get(self, name):
        return self.tools.get(name)

    def list_tools(self):
        return list(self.tools.values())

    def get_tool_schemas(self):
        return [
            tool.get_schema()
            for tool in self.tools.values()
        ]

    def count(self):
        return len(self.tools)

    def has(self, name):
        return name in self.tools

    def execute(self, name, **kwargs):
        tool = self.get(name)

        if tool is None:
            raise ValueError(
                f"Tool '{name}' is not registered."
            )

        return tool.execute(**kwargs)