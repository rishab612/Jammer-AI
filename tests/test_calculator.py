import unittest
from tools.calculator import CalculatorTool


class TestCalculatorTool(unittest.TestCase):

    def setUp(self):
        self.calculator = CalculatorTool()

    def test_multiplication(self):
        self.assertEqual(self.calculator.execute("125 * 48"), 6000)

    def test_addition(self):
        self.assertEqual(self.calculator.execute("100 + 27"), 127)

    def test_subtraction(self):
        self.assertEqual(self.calculator.execute("150 - 70"), 80)

    def test_power(self):
        self.assertEqual(self.calculator.execute("2 ** 10"), 1024)

    def test_division(self):
        self.assertEqual(self.calculator.execute("100 / 4"), 25)

    def test_division_by_zero(self):
        with self.assertRaises((ValueError, ZeroDivisionError)):
            self.calculator.execute("10 / 0")

    def test_empty_expression(self):
        with self.assertRaises(ValueError):
            self.calculator.execute("")

    def test_rejects_unsafe_expression(self):
        with self.assertRaises((ValueError, TypeError)):
            self.calculator.execute("__import__('os').system('whoami')")


if __name__ == "__main__":
    unittest.main()
