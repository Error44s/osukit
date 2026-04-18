"""
The MIT License (MIT)

Copyright (c) 2026 Error44s

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from pathlib import Path

from osukit import (
    create_golden_case,
    load_golden_cases,
    run_golden_case,
    run_golden_suite,
    save_golden_cases,
)


DATA = Path(__file__).parent / "data" / "sample_std.osu"


def test_create_and_run_golden_case_passes_roundtrip(tmp_path):
    case = create_golden_case(
        name="sample_fc",
        beatmap_path=str(DATA),
        accuracy=99.2,
        combo=5,
        misses=0,
    )

    result = run_golden_case(case)

    assert result.passed is True
    assert result.difficulty.stars > 0
    assert result.performance.pp >= 0
    assert result.difficulty_checks
    assert result.performance_checks

    out = tmp_path / "goldens.json"
    save_golden_cases([case], out)
    loaded = load_golden_cases(out)
    loaded_result = run_golden_case(loaded[0])

    assert loaded_result.passed is True
    assert loaded_result.case_name == "sample_fc"


def test_golden_suite_detects_regression():
    case = create_golden_case(name="sample_regression", beatmap_path=str(DATA), accuracy=100.0)
    case.performance.pp += 10.0

    report = run_golden_suite([case])

    assert report.passed is False
    assert report.failed_cases == 1
    assert any(not c.passed for c in report.results[0].performance_checks)


def test_markdown_report_contains_key_fields():
    case = create_golden_case(name="sample_report", beatmap_path=str(DATA), accuracy=97.5, misses=1)
    report = run_golden_suite([case])
    md = report.to_markdown()

    assert "PP Accuracy Benchmark Report" in md
    assert "sample_report" in md
    assert "Stars:" in md
    assert "PP:" in md
