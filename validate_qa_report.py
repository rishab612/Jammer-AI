
import json
from pathlib import Path

REPORT_PATH = Path(__file__).resolve().parent / "reports" / "qa_report.json"

VALID_STATUSES = {
    "passed",
    "failed",
    "error",
    "skipped",
    "expected_failure",
    "unexpected_success",
}


def main():
    if not REPORT_PATH.is_file():
        print(f"FAIL: Report not found: {REPORT_PATH}")
        return 1

    try:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: Cannot read valid JSON: {error}")
        return 1

    summary = report.get("summary")
    records = report.get("tests")

    if not isinstance(summary, dict) or not isinstance(records, list):
        print("FAIL: Missing or invalid summary/tests fields.")
        return 1

    errors = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"Test record {index} is not an object.")
            continue

        if not isinstance(record.get("test"), str):
            errors.append(f"Test record {index} has no valid test ID.")

        if record.get("status") not in VALID_STATUSES:
            errors.append(f"Test record {index} has an unknown status.")

    counts = {
        "tests_run": len(records),
        "passed": sum(r.get("status") == "passed" for r in records
                      if isinstance(r, dict)),
        "failed": sum(r.get("status") == "failed" for r in records
                      if isinstance(r, dict)),
        "errors": sum(r.get("status") == "error" for r in records
                      if isinstance(r, dict)),
        "skipped": sum(r.get("status") == "skipped" for r in records
                       if isinstance(r, dict)),
        "expected_failures": sum(
            r.get("status") == "expected_failure"
            for r in records if isinstance(r, dict)
        ),
        "unexpected_successes": sum(
            r.get("status") == "unexpected_success"
            for r in records if isinstance(r, dict)
        ),
    }

    for key, actual in counts.items():
        if summary.get(key) != actual:
            errors.append(
                f"{key}: summary={summary.get(key)!r}, records={actual}"
            )

    if errors:
        print("QA REPORT VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("QA REPORT VALIDATION: PASS")
    print(f"Tests recorded: {counts['tests_run']}")
    print(f"Passed: {counts['passed']}")
    print(f"Failed: {counts['failed']}")
    print(f"Errors: {counts['errors']}")
    print(f"Report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
