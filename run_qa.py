import argparse
import json
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"
REPORTS_DIR = PROJECT_ROOT / "reports"


class QAResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_records = []

    def startTest(self, test):
        test._qa_started_at = time.perf_counter()
        super().startTest(test)

    def record(self, test, status, details=""):
        started = getattr(test, "_qa_started_at", time.perf_counter())
        self.test_records.append({
            "test": test.id(),
            "status": status,
            "duration_seconds": round(time.perf_counter() - started, 4),
            "details": details[-4000:] if details else ""
        })

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, "failed", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, "skipped", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record(test, "expected_failure", self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, "unexpected_success")


class QAResultRunner(unittest.TextTestRunner):
    resultclass = QAResult


def main():
    parser = argparse.ArgumentParser(
        description="Run Jammer AI automated QA tests."
    )
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="Test filename pattern (default: test_*.py)"
    )
    parser.add_argument(
        "--report",
        default="reports/qa_report.json",
        help="Report path relative to the project root"
    )
    args = parser.parse_args()

    if not TESTS_DIR.is_dir():
        print(f"ERROR: Test directory not found: {TESTS_DIR}")
        return 2

    print("=" * 60)
    print("JAMMER AI - AUTOMATED QA")
    print("=" * 60)
    print(f"Project: {PROJECT_ROOT}")
    print(f"Tests:   {TESTS_DIR}")
    print()

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(TESTS_DIR),
        pattern=args.pattern,
        top_level_dir=str(PROJECT_ROOT)
    )

    if suite.countTestCases() == 0:
        print("ERROR: No tests discovered.")
        return 2

    started_at = time.perf_counter()
    runner = QAResultRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - started_at

    passed = sum(
    record["status"] == "passed"
    for record in result.test_records
)
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    expected_failures = len(result.expectedFailures)
    unexpected_successes = len(result.unexpectedSuccesses)

    report = {
        "application": "Jammer AI",
        "report_generated_at": datetime.now().astimezone().isoformat(),
        "python_version": sys.version,
        "test_directory": str(TESTS_DIR),
        "duration_seconds": round(elapsed, 4),
        "summary": {
            "tests_run": result.testsRun,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "expected_failures": expected_failures,
            "unexpected_successes": unexpected_successes,
            "successful": result.wasSuccessful()
                and unexpected_successes == 0
        },
        "tests": result.test_records
    }

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except OSError as error:
        print(f"\nERROR: Could not save report: {error}")
        return 2

    print("\n" + "=" * 60)
    print("QA SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Passed:    {passed}")
    print(f"Failed:    {failed}")
    print(f"Errors:    {errors}")
    print(f"Skipped:   {skipped}")
    print(f"Duration:  {elapsed:.3f} seconds")
    print(f"Report:    {report_path}")
    print(
        "Overall:   "
        + ("PASS" if report["summary"]["successful"] else "FAIL")
    )

    return 0 if report["summary"]["successful"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

