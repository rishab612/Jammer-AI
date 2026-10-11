import ast
import operator

from tools.base import BaseTool


class CalculatorTool(BaseTool):
    """
    Safe calculator tool for mathematical expressions.
    """

    name = "calculator"

    description = (
        "Perform basic mathematical calculations using numbers, "
        "addition, subtraction, multiplication, division, "
        "percentages, powers, and parentheses."
    )

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def execute(self, expression):
        """
        Safely evaluate a mathematical expression.
        """

        if not isinstance(expression, str):
            raise TypeError("Expression must be a string.")

        expression = expression.strip()

        if not expression:
            raise ValueError("Expression cannot be empty.")

        try:
            tree = ast.parse(expression, mode="eval")
            result = self._evaluate(tree.body)

        except ZeroDivisionError:
            raise ValueError("Cannot divide by zero.")

        except (SyntaxError, ValueError, TypeError):
            raise ValueError(
                f"Invalid mathematical expression: {expression}"
            )

        return result

    def _evaluate(self, node):

        if isinstance(node, ast.Constant):

            if isinstance(node.value, (int, float)):
                return node.value

            raise ValueError("Only numbers are allowed.")

        if isinstance(node, ast.BinOp):

            operator_function = self.OPERATORS.get(type(node.op))

            if operator_function is None:
                raise ValueError("Operator is not allowed.")

            left = self._evaluate(node.left)
            right = self._evaluate(node.right)

            return operator_function(left, right)

        if isinstance(node, ast.UnaryOp):

            operator_function = self.OPERATORS.get(type(node.op))

            if operator_function is None:
                raise ValueError("Operator is not allowed.")

            operand = self._evaluate(node.operand)

            return operator_function(operand)

        raise ValueError(
            "Only basic mathematical expressions are supported."
        )