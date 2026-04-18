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

from osukit import Beatmap, Performance, StdTuningProfile, build_calibration_preset, optimize_with_preset, load_golden_cases


def test_hd_tuning_changes_hidden_bonus_debug_values():
    bm = Beatmap(path="tests/data/sample_std.osu")
    base = Performance(accuracy=99.0, mods=8).calculate(bm)
    tuned = Performance(accuracy=99.0, mods=8, tuning=StdTuningProfile(hidden_high_ar_weight=0.12)).calculate(bm)

    assert "hd_bonus_aim" in base.debug
    assert tuned.debug["tuning_hidden_high_ar_weight"] == 0.12
    assert tuned.debug["hd_bonus_aim"] >= base.debug["hd_bonus_aim"]


def test_dt_tuning_changes_dt_debug_values():
    bm = Beatmap(path="tests/data/sample_std.osu")
    base = Performance(accuracy=98.0, mods=64).calculate(bm)
    tuned = Performance(accuracy=98.0, mods=64, tuning=StdTuningProfile(dt_speed_weight=0.08)).calculate(bm)

    assert "dt_speed_bonus" in base.debug
    assert tuned.debug["tuning_dt_speed_weight"] == 0.08
    assert tuned.debug["dt_speed_bonus"] >= base.debug["dt_speed_bonus"]


def test_hd_dt_presets_optimize_without_error():
    cases = load_golden_cases("tests/data/sample_golden_cases.json")
    hd_outcome = optimize_with_preset(cases, build_calibration_preset("hd_focus"))
    dt_outcome = optimize_with_preset(cases, build_calibration_preset("dt_focus"))

    assert hd_outcome.cases_evaluated >= 1
    assert dt_outcome.cases_evaluated >= 1
    assert hd_outcome.weighted_error >= 0.0
    assert dt_outcome.weighted_error >= 0.0
