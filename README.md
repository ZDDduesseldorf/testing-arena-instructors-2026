# Testing Arena – Instructor Package 2026

This repository contains the mutation-test runner used for a lab course on code testing in the DAISY Software Engineering course.

The repository is intentionally public. The faulty implementations are kept
separate from the student starter repository and are identified only by IDs
(`M001` ... `M010`). They are **not security-sensitive secrets** and the separation
is meant to prevent accidental spoilers during the exercise, not deliberate
inspection.

## Student-side assumptions

The runner expects to be started from a student repository containing:

```text
weather.py
 tests/
   ... pytest files ...
```

The student tests should import the public functions from `weather.py`.

The expected public API is:

```python
parse_time(time_text)
parse_measurement(line)
filter_by_temperature(measurements, lower, upper)
average_temperature(measurements, city)
hottest_measurement(measurements)
```

## Running the arena from a student repository

For local development of the course material:

```bash
uv run --with "testing-arena-mutants @ git+https://github.com/ZDDduesseldorf/testing-arena-instructors-2026.git" testing-arena
```

For the actual course, pin the dependency to a tag so every group uses the
same arena version, for example:

```bash
uv run --with "testing-arena-mutants @ git+https://github.com/ZDDduesseldorf/testing-arena-instructors-2026.git@v2026.1" testing-arena
```

Alternative without the console script:

```bash
uv run --with "testing-arena-mutants @ git+https://github.com/ZDDduesseldorf/testing-arena-instructors-2026.git@v2026.1" \
  python -m testing_arena_mutants.runner
```

## What the runner does

1. Copies the student repository into a temporary working directory.
2. Runs the student tests against the unchanged reference implementation.
3. Stops immediately if the reference implementation does not pass.
4. Replaces `weather.py` temporarily with each arena variant.
5. Runs the complete student test suite in a fresh pytest subprocess.
6. Classifies each variant as:
   - **killed**: at least one student test fails;
   - **survived**: all student tests still pass;
   - **arena error**: pytest cannot run normally (collection/internal error).
7. Prints only mutation IDs and the final score by default.
8. Writes the same result as Markdown to `$GITHUB_STEP_SUMMARY` when running in GitHub Actions.

The student's checkout itself is never modified.

## Recommended GitHub Actions workflow in the student template

```yaml
name: Mutation Test Arena

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  mutation-arena:
    runs-on: ubuntu-latest
    steps:
      - name: Check out student repository
        uses: actions/checkout@v5

      - name: Install uv
        uses: astral-sh/setup-uv@v10

      - name: Run mutation arena
        run: >-
          uv run
          --with "testing-arena-mutants @ git+https://github.com/ZDDduesseldorf/testing-arena-instructors-2026.git@v2026.1"
          testing-arena
```

The workflow deliberately uses `workflow_dispatch`: students decide when their
test suite is mature enough for another arena run.

## Runner options

```text
--root PATH       student repository root; defaults to current directory
--target PATH     target Python file; defaults to weather.py
--tests PATH      pytest path; defaults to tests
--debug           show pytest output for killed/error cases
```

`--debug` is intended for instructors. The normal course workflow should omit
it, because pytest failure output can make the mutation easier to infer.

## Development

```bash
uv sync
uv run pytest
```

The package contains ten mutation cases. File names deliberately carry no
description of the underlying defect.
