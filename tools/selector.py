
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import re


@dataclass
class ToolSelection:
    """Represents Jammer's tool-selection decision."""

    use_tool: bool
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self):
        return {
            "use_tool": self.use_tool,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "reason": self.reason,
        }


class ToolSelector:
    """Rule-based selector for Jammer AI's local tools."""

    def __init__(self, registry):
        self.registry = registry

    def select(self, user_input):
        if not isinstance(user_input, str):
            raise TypeError("User input must be a string.")

        text = user_input.lower().strip()

        if not text:
            return ToolSelection(
                use_tool=False,
                reason="Empty user request.",
            )

        # Prevent recognized terminal commands from being routed
        # to the normal tools.
        if self._looks_like_terminal_command(user_input):
            return ToolSelection(
                use_tool=False,
                reason="The input appears to be a terminal command.",
            )

        # Date and time
        if self._looks_like_datetime(text):
            return ToolSelection(
                use_tool=True,
                tool_name="datetime",
                arguments={
                    "mode": self._detect_datetime_mode(text),
                },
                reason="The request asks for the current date or time.",
            )

        # System information
        if self._looks_like_system_info(text):
            return ToolSelection(
                use_tool=True,
                tool_name="system_info",
                arguments={
                    "category": self._detect_system_category(text),
                },
                reason="The request asks about the local computer.",
            )

        # Filesystem inspection
        if self._looks_like_filesystem(text):
            action = self._detect_filesystem_action(text)
            path = self._extract_filesystem_path(user_input, action)

            return ToolSelection(
                use_tool=True,
                tool_name="filesystem",
                arguments={
                    "action": action,
                    "path": path,
                },
                reason="The request requires filesystem inspection.",
            )

        # Calculator
        if self._looks_like_calculation(text):
            expression = self._extract_expression(user_input)

            if expression:
                return ToolSelection(
                    use_tool=True,
                    tool_name="calculator",
                    arguments={"expression": expression},
                    reason="The request appears to require a calculation.",
                )

        return ToolSelection(
            use_tool=False,
            reason="No available tool appears necessary.",
        )

    # =====================================================
    # TERMINAL COMMAND GUARD
    # =====================================================

    def _looks_like_terminal_command(self, original_text):
        text = original_text.strip()

        patterns = [
            (
                r"^\s*(?:PS\s+[^>]*>\s*)?"
                r"(?:Get-Content|Get-ChildItem|Set-Location|"
                r"New-Item|Remove-Item|Test-Path|Get-Process|"
                r"Get-Service|Get-Command)\b"
            ),
            (
                r"^\s*(?:python|py|pip|git|npm|node|curl|winget|"
                r"ipconfig|ping|tracert|netstat|dir|cd|type|"
                r"mkdir|rmdir|copy|move|del|cls|echo)\b"
            ),
            r"^\s*(?:PS\s+)?[A-Za-z]:\\.*>\s*",
            r"\b(?:powershell|cmd\.exe)\s+(?:/c|-command)\b",
            r"^\s*&\s*(?:python|py|powershell|pwsh|cmd|node)\b",
            (
                r"^\s*(?:Start-Process|Invoke-Expression|"
                r"Invoke-Command|Start-Job|schtasks|sc\.exe)\b"
            ),
        ]

        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        )

    # =====================================================
    # CALCULATOR
    # =====================================================

    def _looks_like_calculation(self, text):
        text = text.strip().lower()

        # Direct arithmetic expressions, e.g. 125 * 48.
        expression_pattern = r"^[\d\s()+\-*/%^.]+$"

        if re.fullmatch(expression_pattern, text):
            return (
                any(char.isdigit() for char in text)
                and any(char in text for char in "+-*/%^")
            )

        # Natural-language arithmetic with explicit operands.
        number = r"[-+]?\d+(?:\.\d+)?"

        natural_patterns = [
            rf"^multiply\s+{number}\s+by\s+{number}$",
            rf"^divide\s+{number}\s+by\s+{number}$",
            rf"^add\s+{number}\s+and\s+{number}$",
            rf"^subtract\s+{number}\s+from\s+{number}$",
        ]

        if any(
            re.fullmatch(pattern, text)
            for pattern in natural_patterns
        ):
            return True

        # Symbolic expressions introduced by common phrases.
        calculation_phrases = [
            "calculate ",
            "compute ",
            "solve ",
            "what is ",
            "what's ",
            "how much is ",
        ]

        return (
            any(text.startswith(phrase) for phrase in calculation_phrases)
            and any(char.isdigit() for char in text)
            and any(char in text for char in "+-*/%^×÷")
        )

    def _extract_expression(self, text):
        cleaned = text.strip()
        lowered = cleaned.lower()

        number = r"([-+]?\d+(?:\.\d+)?)"

        # Convert natural-language arithmetic to safe expressions.
        natural_patterns = [
            (
                rf"^multiply\s+{number}\s+by\s+{number}$",
                r"\1 * \2",
            ),
            (
                rf"^divide\s+{number}\s+by\s+{number}$",
                r"\1 / \2",
            ),
            (
                rf"^add\s+{number}\s+and\s+{number}$",
                r"\1 + \2",
            ),
            (
                rf"^subtract\s+{number}\s+from\s+{number}$",
                r"\2 - \1",
            ),
        ]

        for pattern, replacement in natural_patterns:
            if re.fullmatch(pattern, lowered):
                return re.sub(pattern, replacement, lowered)

        # Remove recognized introductory phrases.
        prefixes = [
            "calculate",
            "compute",
            "solve",
            "what is",
            "what's",
            "how much is",
        ]

        for prefix in prefixes:
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break

        cleaned = cleaned.rstrip("?!").strip()

        # Normalize mathematical symbols.
        replacements = {
            "×": "*",
            "÷": "/",
            "^": "**",
        }

        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned or None

    # =====================================================
    # DATE / TIME
    # =====================================================

    def _looks_like_datetime(self, text):
        keywords = [
            "current time",
            "what time",
            "time now",
            "current date",
            "what date",
            "date today",
            "day today",
            "what day",
            "today's date",
            "today",
        ]

        return any(keyword in text for keyword in keywords)

    def _detect_datetime_mode(self, text):
        if "time" in text:
            return "time"

        if "day" in text:
            return "day"

        if "date" in text or "today" in text:
            return "date"

        return "full"

    # =====================================================
    # SYSTEM INFORMATION
    # =====================================================

    def _looks_like_system_info(self, text):
        keywords = [
            "system information",
            "system info",
            "computer information",
            "computer specs",
            "computer specification",
            "pc specs",
            "pc specification",
            "cpu information",
            "cpu info",
            "cpu usage",
            "processor information",
            "processor usage",
            "ram",
            "ram usage",
            "memory usage",
            "memory information",
            "python version",
            "python information",
            "operating system",
            "os information",
            "os info",
            "system specifications",
        ]

        return any(keyword in text for keyword in keywords)

    def _detect_system_category(self, text):
        if "cpu" in text or "processor" in text:
            return "cpu"

        if "ram" in text or "memory" in text:
            return "memory"

        if "python" in text:
            return "python"

        if any(
            term in text
            for term in ["operating system", "os information", "os info"]
        ):
            return "os"

        return "all"

    # =====================================================
    # FILESYSTEM
    # =====================================================

    def _looks_like_filesystem(self, text):
        keywords = [
            "list files",
            "list folders",
            "list directory",
            "show files",
            "show folders",
            "show directory",
            "directory contents",
            "folder contents",
            "file information",
            "file info",
            "file details",
            "folder information",
            "folder info",
            "information about",
            "details about",
            "info about",
        ]

        return (
            any(keyword in text for keyword in keywords)
            or bool(re.search(r"[A-Za-z]:[\\/]", text))
        )

    def _detect_filesystem_action(self, text):
        if any(term in text for term in ["exist", "exists", "check if"]):
            return "exists"

        if any(term in text for term in ["info", "information", "details"]):
            return "info"

        return "list"

    def _extract_filesystem_path(self, original_text, action):
        text = original_text.strip()

        # Explicit Windows paths.
        windows_path_match = re.search(
            r"([A-Za-z]:[\\/].*?)(?:\s+(?:exist|exists|is|are|"
            r"directory|folder|file)\b|[?!.,]*$)",
            text,
            re.IGNORECASE,
        )

        if windows_path_match:
            return windows_path_match.group(1).strip().rstrip(".,!?")

        # Quoted paths.
        quoted_match = re.search(r'"([^"]+)"', text)

        if quoted_match:
            return quoted_match.group(1).strip()

        # Paths following common prepositions.
        patterns = [
            r"\bin\s+(.+?)(?:\s+(?:directory|folder))?$",
            r"\binside\s+(.+?)(?:\s+(?:directory|folder))?$",
            r"\bat\s+(.+)$",
            r"\b(?:about|for)\s+(.+?)(?:[?!.,]+)?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                return match.group(1).strip().rstrip(".,!?")

        file_match = re.search(
            r"\bfile\s+([^\s]+)",
            text,
            re.IGNORECASE,
        )

        if file_match:
            return file_match.group(1).strip()

        folder_match = re.search(
            r"\bfolder\s+([^\s]+)",
            text,
            re.IGNORECASE,
        )

        if folder_match:
            return folder_match.group(1).strip()

        return "."
