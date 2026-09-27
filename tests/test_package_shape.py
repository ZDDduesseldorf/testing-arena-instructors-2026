from pathlib import Path

import testing_arena_mutants.runner as runner

EXPECTED_FUNCTIONS = {
    "parse_time",
    "parse_measurement",
    "filter_by_temperature",
    "average_temperature",
    "hottest_measurement",
}


def test_exactly_ten_mutation_cases_exist():
    mutation_files = runner._mutation_files()
    assert [path.stem for path in mutation_files] == [f"m{i:03d}" for i in range(1, 11)]


def test_each_mutation_exposes_expected_functions():
    for path in runner._mutation_files():
        namespace = {}
        exec(Path(path).read_text(encoding="utf-8"), namespace)
        assert EXPECTED_FUNCTIONS <= set(namespace)
