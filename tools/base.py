from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    Base class for every Jammer tool.
    """

    name = "base_tool"
    description = "Base Jammer tool."

    @abstractmethod
    def execute(self, **kwargs):
        """
        Execute the tool.

        Every tool must implement this method.
        """
        pass

    def get_schema(self):
        """
        Return basic information about the tool.
        """

        return {
            "name": self.name,
            "description": self.description
        }