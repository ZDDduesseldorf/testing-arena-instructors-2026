"""Run a student's pytest suite against a collection of faulty implementations."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

IGNORED_NAMES = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    "htmlcov",
}


@dataclass(frozen=True)
class PytestResult:
    returncode: int
    output: str


@dataclass(frozen=True)
class MutationResult:
    mutation_id: str
    status: str  # "killed", "survived", "error"
    output: str = ""


def _ignore_copy(directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in IGNORED_NAMES}
    ignored.update(name for name in names if name.endswith(".pyc"))
    return ignored


def _run_pytest(workspace: Path, tests_path: str) -> PytestResult:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(workspace)
        if not existing_pythonpath
        else os.pathsep.join([str(workspace), existing_pythonpath])
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    command = [
        sys.executable,
        "-m",
        "pytest",
        tests_path,
        "-q",
        "--disable-warnings",
        "--maxfail=1",
        "--cache-clear",
    ]
    completed = subprocess.run(
        command,
        cwd=workspace,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return PytestResult(completed.returncode, completed.stdout)


def _clear_bytecode(workspace: Path) -> None:
    for cache_dir in workspace.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)


def _mutation_files() -> list[Path]:
    cases_dir = Path(__file__).resolve().parent / "cases"
    return sorted(cases_dir.glob("m[0-9][0-9][0-9].py"))


def _tail(text: str, lines: int = 20) -> str:
    chunks = text.rstrip().splitlines()
    return "\n".join(chunks[-lines:])


def _write_github_summary(
    reference_ok: bool,
    results: list[MutationResult],
) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    killed = sum(result.status == "killed" for result in results)
    survived = sum(result.status == "survived" for result in results)
    errors = sum(result.status == "error" for result in results)

    lines = [
        "## 🧪 Mutation Test Arena",
        "",
        f"**Reference implementation:** {'✅ accepted' if reference_ok else '❌ rejected'}",
        "",
    ]

    if results:
        lines.extend([
            "| Mutation | Result |",
            "|---|---|",
        ])
        for result in results:
            label = {
                "killed": "💀 detected",
                "survived": "🧟 survived",
                "error": "⚠️ arena error",
            }[result.status]
            lines.append(f"| {result.mutation_id} | {label} |")

        lines.extend([
            "",
            f"### Score: **{killed} / {len(results)}** faulty implementations detected",
            "",
            f"Survived: **{survived}** · Arena errors: **{errors}**",
            "",
            "> A surviving mutation means that a faulty implementation still satisfies your current tests.",
        ])

    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_console_summary(results: list[MutationResult]) -> None:
    killed = sum(result.status == "killed" for result in results)
    survived = sum(result.status == "survived" for result in results)
    errors = sum(result.status == "error" for result in results)

    print("\nMutation Test Arena")
    print("===================")
    print("Reference implementation: PASS ✅\n")

    for result in results:
        label = {
            "killed": "killed\t💀",
            "survived": "survived\t🧟",
            "error": "error\t⚠️",
        }[result.status]
        print(f"{result.mutation_id}: {label}")

    print(f"\nScore: {killed} / {len(results)} faulty implementations detected")
    if survived:
        print(f"{survived} faulty implementation(s) still satisfy your tests.")
    if errors:
        print(f"{errors} arena run(s) ended with an unexpected pytest/collection error.")


def run_arena(
    root: Path,
    target: str,
    tests_path: str,
    debug: bool = False,
) -> int:
    root = root.resolve()
    target_path = root / target
    tests = root / tests_path

    if not target_path.is_file():
        print(f"ERROR: target file not found: {target_path}", file=sys.stderr)
        return 3
    if not tests.exists():
        print(f"ERROR: tests path not found: {tests}", file=sys.stderr)
        return 3

    mutations = _mutation_files()
    if not mutations:
        print("ERROR: no mutation cases found in arena package.", file=sys.stderr)
        return 3

    with tempfile.TemporaryDirectory(prefix="testing-arena-") as temp_dir:
        workspace = Path(temp_dir) / "student-repo"
        shutil.copytree(root, workspace, ignore=_ignore_copy)

        print("Checking student tests against the reference implementation...")
        reference_result = _run_pytest(workspace, tests_path)
        if reference_result.returncode != 0:
            print("\n❌ Arena stopped: your tests reject the reference implementation.")
            print("Fix the regular test suite before running the mutation arena.\n")
            print(_tail(reference_result.output, 30))
            _write_github_summary(False, [])
            return 2

        original_target = (workspace / target).read_text(encoding="utf-8")
        results: list[MutationResult] = []

        for mutation_file in mutations:
            mutation_id = mutation_file.stem.upper()
            print(f"Running {mutation_id}...", flush=True)

            mutant_source = mutation_file.read_text(encoding="utf-8")
            (workspace / target).write_text(mutant_source, encoding="utf-8")
            _clear_bytecode(workspace)

            result = _run_pytest(workspace, tests_path)

            if result.returncode == 0:
                status = "survived"
            elif result.returncode == 1:
                status = "killed"
            else:
                status = "error"

            results.append(MutationResult(mutation_id, status, result.output))

            if debug and status != "survived":
                print(_tail(result.output, 20))

        (workspace / target).write_text(original_target, encoding="utf-8")

    _print_console_summary(results)
    _write_github_summary(True, results)

    if any(result.status == "error" for result in results):
        return 3
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the student's tests against the HSD/ZDD mutation arena."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Student repository root (default: current directory).",
    )
    parser.add_argument(
        "--target",
        default="weather.py",
        help="Python file replaced by arena variants (default: weather.py).",
    )
    parser.add_argument(
        "--tests",
        default="tests",
        help="Path passed to pytest (default: tests).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show pytest output for detected mutations and arena errors.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(run_arena(args.root, args.target, args.tests, args.debug))


if __name__ == "__main__":
    main()
