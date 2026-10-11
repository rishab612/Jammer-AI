from pathlib import Path

from tools.base import BaseTool


class FileSystemTool(BaseTool):
    """
    Read-only local filesystem tool.
    """

    name = "filesystem"

    description = (
        "Inspect the local filesystem by listing directories, "
        "checking whether paths exist, and getting basic file information."
    )

    def execute(self, action, path="."):
        """
        Execute a filesystem operation.
        """

        if not isinstance(action, str):
            raise TypeError("Action must be a string.")

        action = action.lower().strip()

        target = Path(path).expanduser()

        if action == "list":
            return self._list_directory(target)

        if action == "exists":
            return self._exists(target)

        if action == "info":
            return self._file_info(target)

        raise ValueError(
            "Invalid action. Use: list, exists, or info."
        )

    def _list_directory(self, path):

        if not path.exists():
            raise FileNotFoundError(
                f"Path does not exist: {path}"
            )

        if not path.is_dir():
            raise ValueError(
                f"Path is not a directory: {path}"
            )

        items = []

        for item in sorted(
            path.iterdir(),
            key=lambda x: (not x.is_dir(), x.name.lower())
        ):
            item_type = "DIR" if item.is_dir() else "FILE"

            items.append({
                "name": item.name,
                "type": item_type
            })

        return items

    def _exists(self, path):

        return {
            "path": str(path.resolve()),
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_directory": path.is_dir()
        }

    def _file_info(self, path):

        if not path.exists():
            raise FileNotFoundError(
                f"Path does not exist: {path}"
            )

        stat = path.stat()

        return {
            "path": str(path.resolve()),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "size_bytes": stat.st_size if path.is_file() else None
        }