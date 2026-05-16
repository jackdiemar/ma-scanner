#!/usr/bin/env python3
"""
Run the standard historical case factory validation suite.

This runner calls the existing validators, captures their output, and writes one
batch-scoped suite report:
  - data/historical_cases/{batch_name}_validation_suite_report.md

It preserves any side-effect reports written by individual validators so the only
net file mutation from this runner is the suite report itself.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_DIR = REPO_ROOT / "data" / "historical_cases"

ALIGNMENT_VALIDATOR = REPO_ROOT / "src" / "historical_case_tools" / "validate_batch_alignment.py"
SOURCE_VALIDATOR = REPO_ROOT / "src" / "historical_case_tools" / "validate_source_evidence_integrity.py"


@dataclass(frozen=True)
class ValidatorRun:
    name: str
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    result: str
    warnings: int | None
    failures: int | None
    scope: str
    skipped: bool = False
    missing: bool = False


def preserve_path(path: Path) -> tuple[bool, bytes]:
    if not path.exists():
        return False, b""
    return True, path.read_bytes()


def restore_path(path: Path, existed: bool, content: bytes) -> None:
    if existed:
        path.write_bytes(content)
    elif path.exists():
        path.unlink()


def result_from_output(name: str, stdout: str, exit_code: int, skipped: bool = False, missing: bool = False) -> str:
    if skipped:
        return "SKIPPED"
    if missing:
        return "FAIL"

    patterns = {
        "alignment": r"Batch alignment validation:\s*(PASS|WARN|FAIL)",
        "source_evidence": r"Source evidence integrity:\s*(PASS|WARN|FAIL)",
    }
    match = re.search(patterns.get(name, r"\b(PASS|WARN|FAIL)\b"), stdout)
    if match:
        return match.group(1)
    return "PASS" if exit_code == 0 else "FAIL"


def count_from_output(label: str, stdout: str) -> int | None:
    match = re.search(rf"^{label}:\s*(\d+)\s*$", stdout, re.MULTILINE)
    if match:
        return int(match.group(1))
    bracket_labels = {"Warnings": "WARN", "Failures": "FAIL"}
    bracket_count = len(re.findall(rf"^\[{bracket_labels[label]}\]", stdout, re.MULTILINE))
    return bracket_count if bracket_count else None


def command_text(command: list[str]) -> str:
    return " ".join(command).replace(str(REPO_ROOT) + "/", "")


def run_validator(
    *,
    name: str,
    validator_path: Path,
    args: list[str],
    side_effect_report: Path,
    scope: str,
) -> ValidatorRun:
    command = [sys.executable, str(validator_path), *args]
    display_command = ["python3", str(validator_path.relative_to(REPO_ROOT)), *args]

    if not validator_path.exists():
        return ValidatorRun(
            name=name,
            command=display_command,
            exit_code=127,
            stdout="",
            stderr=f"Missing validator: {validator_path.relative_to(REPO_ROOT)}",
            result="FAIL",
            warnings=0,
            failures=1,
            scope=scope,
            missing=True,
        )

    existed, content = preserve_path(side_effect_report)
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
    restore_path(side_effect_report, existed, content)

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    result = result_from_output(name, stdout, completed.returncode)
    return ValidatorRun(
        name=name,
        command=display_command,
        exit_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        result=result,
        warnings=count_from_output("Warnings", stdout),
        failures=count_from_output("Failures", stdout),
        scope=scope,
    )


def skipped_run(name: str, reason: str, scope: str) -> ValidatorRun:
    return ValidatorRun(
        name=name,
        command=[],
        exit_code=0,
        stdout=reason,
        stderr="",
        result="SKIPPED",
        warnings=None,
        failures=None,
        scope=scope,
        skipped=True,
    )


def overall_result(runs: list[ValidatorRun]) -> str:
    active = [run for run in runs if not run.skipped]
    if any(run.result == "FAIL" or run.exit_code != 0 for run in active):
        return "FAIL"
    if any(run.result == "WARN" or (run.warnings or 0) > 0 for run in active):
        return "WARN"
    return "PASS"


def next_action(overall: str, alignment: ValidatorRun | None, source: ValidatorRun | None) -> str:
    if overall == "PASS":
        return "Proceed with the next case factory step if the repo state is clean."
    if alignment and alignment.result == "FAIL":
        return "Stop and resolve batch alignment before running package or adjudication steps."
    if source and source.result == "FAIL":
        return "Do not mutate data automatically. Review the source evidence integrity report and fix evidence/date issues in a separate, intentional cleanup."
    return "Review warnings before proceeding."


def report_path(batch_name: str) -> Path:
    return HISTORICAL_DIR / f"{batch_name}_validation_suite_report.md"


def write_report(batch_name: str, strict: bool, runs: list[ValidatorRun], overall: str) -> Path:
    path = report_path(batch_name)
    timestamp = datetime.now().isoformat(timespec="seconds")
    alignment = next((run for run in runs if run.name == "alignment"), None)
    source = next((run for run in runs if run.name == "source_evidence"), None)

    lines = [
        f"# Case Factory Validation Suite Report: {batch_name}",
        "",
        f"- Timestamp: {timestamp}",
        f"- Batch name: {batch_name}",
        f"- Mode: {'strict' if strict else 'non-strict'}",
        f"- Overall result: {overall}",
        f"- Next recommended action: {next_action(overall, alignment, source)}",
        "",
        "## Summary",
        "",
        "| Validator | Result | Scope | Exit code | Warnings | Failures |",
        "|---|---|---|---:|---:|---:|",
    ]
    for run in runs:
        warnings = "" if run.warnings is None else str(run.warnings)
        failures = "" if run.failures is None else str(run.failures)
        lines.append(f"| {run.name} | {run.result} | {run.scope} | {run.exit_code} | {warnings} | {failures} |")

    lines.extend(["", "## Commands Run", ""])
    for run in runs:
        if run.skipped:
            lines.append(f"- `{run.name}` skipped: {run.stdout}")
        else:
            lines.append(f"- `{command_text(run.command)}`")

    lines.extend(["", "## Findings", ""])
    for run in runs:
        lines.append(f"### {run.name}")
        lines.append("")
        lines.append(f"- Result: {run.result}")
        lines.append(f"- Exit code: {run.exit_code}")
        lines.append(f"- Scope: {run.scope}")
        if run.warnings is not None:
            lines.append(f"- Warnings: {run.warnings}")
        if run.failures is not None:
            lines.append(f"- Failures: {run.failures}")
        if run.missing:
            lines.append("- Failure type: missing validator file")
        lines.append("")
        if run.stdout:
            lines.append("```text")
            lines.append(run.stdout)
            lines.append("```")
        if run.stderr:
            lines.append("")
            lines.append("stderr:")
            lines.append("")
            lines.append("```text")
            lines.append(run.stderr)
            lines.append("```")
        lines.append("")

    lines.extend(
        [
            "## Scope Notes",
            "",
            "- Alignment failures are batch-specific.",
            "- Source evidence integrity failures are global unless the source validator is run with filters.",
            "- This suite does not run the scanner, run package commands, adjudicate cases, or edit source CSVs.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def print_summary(batch_name: str, runs: list[ValidatorRun], overall: str, path: Path) -> None:
    alignment = next((run for run in runs if run.name == "alignment"), None)
    source = next((run for run in runs if run.name == "source_evidence"), None)

    print(f"Case factory validation suite: {overall}")
    print(f"Batch: {batch_name}")
    print(f"Alignment result: {alignment.result if alignment else 'SKIPPED'}")
    print(f"Source evidence result: {source.result if source else 'SKIPPED'}")
    for run in runs:
        warnings = "unknown" if run.warnings is None else str(run.warnings)
        failures = "unknown" if run.failures is None else str(run.failures)
        print(f"{run.name}: exit={run.exit_code} warnings={warnings} failures={failures}")
    print(f"Report: {path.relative_to(REPO_ROOT)}")
    print(f"Next recommended action: {next_action(overall, alignment, source)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standard case factory validation suite.")
    parser.add_argument("--batch-name", required=True, help="Batch name such as batch_71_100")
    parser.add_argument("--strict", action="store_true", help="Pass strict mode through to validators")
    parser.add_argument("--skip-source-evidence", action="store_true", help="Skip source evidence integrity validation")
    parser.add_argument("--skip-alignment", action="store_true", help="Skip batch alignment validation")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    runs: list[ValidatorRun] = []

    if args.skip_alignment:
        runs.append(skipped_run("alignment", "--skip-alignment passed", "batch-specific"))
    else:
        alignment_args = ["--batch-name", args.batch_name]
        if args.strict:
            alignment_args.append("--strict")
        runs.append(
            run_validator(
                name="alignment",
                validator_path=ALIGNMENT_VALIDATOR,
                args=alignment_args,
                side_effect_report=HISTORICAL_DIR / f"{args.batch_name}_alignment_validation_report.md",
                scope="batch-specific",
            )
        )

    if args.skip_source_evidence:
        runs.append(skipped_run("source_evidence", "--skip-source-evidence passed", "global"))
    else:
        source_args = ["--strict"] if args.strict else []
        runs.append(
            run_validator(
                name="source_evidence",
                validator_path=SOURCE_VALIDATOR,
                args=source_args,
                side_effect_report=HISTORICAL_DIR / "source_evidence_integrity_report.md",
                scope="global",
            )
        )

    overall = overall_result(runs)
    path = write_report(args.batch_name, args.strict, runs, overall)
    print_summary(args.batch_name, runs, overall, path)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
