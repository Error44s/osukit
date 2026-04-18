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

from osukit import (
    CalibrationPreset,
    StdTuningProfile,
    build_calibration_preset,
    compare_benchmark_reports,
    infer_case_tags,
    load_golden_cases,
    optimize_with_preset,
    run_golden_suite,
)
from osukit.benchmark import GoldenScoreCase, DifficultyExpectation, PerformanceExpectation


def test_infer_case_tags_adds_mod_and_shape_tags():
    case = GoldenScoreCase(
        name="auto tagged",
        beatmap_path="tests/data/sample_std.osu",
        mods=8 | 64,
        accuracy=99.1,
        difficulty=DifficultyExpectation(stars=0.1, tolerance=10.0),
        performance=PerformanceExpectation(pp=0.1, tolerance=1000.0),
    )
    tags = infer_case_tags(case)
    assert "hd" in tags
    assert "dt" in tags
    assert "accuracy" in tags
    assert any(tag in tags for tag in ("short", "long", "slider-heavy", "aim", "speed"))


def test_compare_benchmark_reports_detects_changes():
    cases = load_golden_cases("tests/data/sample_golden_cases.json")
    baseline = run_golden_suite(cases)
    candidate = run_golden_suite(cases, tuning=StdTuningProfile(final_multiplier=1.02))
    deltas = compare_benchmark_reports(baseline, candidate)
    assert deltas
    assert any(delta.metric == "performance.pp" for delta in deltas)


def test_build_calibration_preset_and_optimize_with_preset():
    preset = build_calibration_preset("hd_focus")
    assert isinstance(preset, CalibrationPreset)
    cases = load_golden_cases("tests/data/sample_golden_cases.json")
    outcome = optimize_with_preset(cases, preset)
    assert outcome.cases_evaluated >= 1
    assert outcome.weighted_error >= 0.0


def test_report_markdown_includes_mod_summary():
    cases = [
        GoldenScoreCase(
            name="hd case",
            beatmap_path="tests/data/sample_std.osu",
            mods=8,
            accuracy=98.5,
            difficulty=DifficultyExpectation(stars=0.1, tolerance=10.0),
            performance=PerformanceExpectation(pp=0.1, tolerance=1000.0),
        )
    ]
    report = run_golden_suite(cases)
    md = report.to_markdown()
    assert "Mod Summary" in md
    assert "HD" in md or "NM" in md
