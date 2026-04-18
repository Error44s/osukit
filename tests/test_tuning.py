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

import unittest

from osukit import (
    Beatmap,
    Performance,
    StdTuningProfile,
    load_golden_cases,
    optimize_standard_tuning,
    run_golden_suite,
)


class TestStdTuning(unittest.TestCase):
    def test_tuning_profile_changes_pp(self):
        bm = Beatmap(path='tests/data/sample_std.osu')
        base = Performance(accuracy=98.5).calculate(bm)
        tuned = Performance(accuracy=98.5, tuning=StdTuningProfile(final_multiplier=1.05)).calculate(bm)
        self.assertGreater(tuned.pp, base.pp)

    def test_golden_suite_accepts_tuning(self):
        cases = load_golden_cases('tests/data/sample_golden_cases.json')
        report = run_golden_suite(cases, tuning=StdTuningProfile(final_multiplier=1.01))
        self.assertGreaterEqual(report.total_cases, 1)

    def test_optimizer_returns_outcome(self):
        cases = load_golden_cases('tests/data/sample_golden_cases.json')
        outcome = optimize_standard_tuning(cases, search_scale=0.02)
        self.assertGreaterEqual(outcome.cases_evaluated, 1)
        self.assertTrue(hasattr(outcome.tuning, 'aim_multiplier'))


if __name__ == '__main__':
    unittest.main()



def test_benchmark_tag_summary():
    from osukit.benchmark import GoldenScoreCase, DifficultyExpectation, PerformanceExpectation, run_golden_suite

    path = "tests/data/sample_std.osu"
    cases = [
        GoldenScoreCase(
            name="hd case",
            beatmap_path=path,
            mods=8,
            accuracy=98.5,
            difficulty=DifficultyExpectation(stars=0.1, tolerance=10.0),
            performance=PerformanceExpectation(pp=0.1, tolerance=1000.0),
            tags=["hd", "aim"],
        ),
        GoldenScoreCase(
            name="dt case",
            beatmap_path=path,
            mods=64,
            accuracy=97.0,
            difficulty=DifficultyExpectation(stars=0.1, tolerance=10.0),
            performance=PerformanceExpectation(pp=0.1, tolerance=1000.0),
            tags=["dt", "speed"],
        ),
    ]
    report = run_golden_suite(cases)
    summary = report.summarize_by_tag()
    assert "hd" in summary
    assert "dt" in summary
    assert summary["hd"]["cases"] == 1.0
    md = report.to_markdown()
    assert "Tag Summary" in md


def test_benchmark_metric_summary_and_focus_recommendations():
    from osukit.benchmark import GoldenScoreCase, DifficultyExpectation, PerformanceExpectation, run_golden_suite

    path = "tests/data/sample_std.osu"
    cases = [
        GoldenScoreCase(
            name="slider heavy case",
            beatmap_path=path,
            accuracy=97.3,
            difficulty=DifficultyExpectation(stars=10.0, tolerance=0.01),
            performance=PerformanceExpectation(pp=1000.0, tolerance=0.01),
            tags=["slider-heavy", "aim"],
        ),
        GoldenScoreCase(
            name="hd speed case",
            beatmap_path=path,
            mods=8,
            accuracy=98.8,
            difficulty=DifficultyExpectation(stars=0.1, tolerance=10.0),
            performance=PerformanceExpectation(pp=0.1, tolerance=1000.0),
            tags=["hd", "speed"],
        ),
    ]
    report = run_golden_suite(cases)
    metric_summary = report.summarize_by_metric()
    focus = report.recommend_focus()

    assert "difficulty.stars" in metric_summary
    assert focus
    assert any(rec.category == "slider-heavy" for rec in focus)
    md = report.to_markdown()
    assert "Metric Summary" in md
    assert "Recommended Focus" in md



def test_weighted_objective_optimizer_returns_weighted_error():
    from osukit import CalibrationObjective, load_golden_cases, optimize_standard_tuning

    cases = load_golden_cases('tests/data/sample_golden_cases.json')
    objective = CalibrationObjective(tag_weights={"hd": 2.0}, metric_weights={"performance.pp": 3.0})
    outcome = optimize_standard_tuning(cases, search_scale=0.02, objective=objective)

    assert outcome.weighted_error >= 0.0
    assert outcome.cases_evaluated >= 1
