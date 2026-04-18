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


def test_slider_tuning_exposes_debug_signals():
    bm = Beatmap(path="tests/data/sample_std.osu")
    base = Performance(accuracy=98.6, slider_end_miss=2).calculate(bm)
    tuned = Performance(accuracy=98.6, slider_end_miss=2, tuning=StdTuningProfile(slider_velocity_weight=0.2)).calculate(bm)

    assert "slider_signal" in base.debug
    assert tuned.debug["tuning_slider_velocity_weight"] == 0.2
    assert tuned.debug["slider_velocity_bonus"] >= base.debug["slider_velocity_bonus"]


def test_aim_speed_tuning_exposes_split_debug_signals():
    bm = Beatmap(path="tests/data/sample_std.osu")
    base = Performance(accuracy=99.1).calculate(bm)
    tuned = Performance(accuracy=99.1, tuning=StdTuningProfile(aim_stream_balance=0.2, speed_stream_balance=0.2)).calculate(bm)

    assert "aim_stream_bonus" in base.debug
    assert "speed_stream_bonus" in base.debug
    assert tuned.debug["tuning_aim_stream_balance"] == 0.2
    assert tuned.debug["tuning_speed_stream_balance"] == 0.2


def test_slider_and_aim_speed_presets_optimize_without_error():
    cases = load_golden_cases("tests/data/sample_golden_cases.json")
    slider_outcome = optimize_with_preset(cases, build_calibration_preset("slider_focus"))
    split_outcome = optimize_with_preset(cases, build_calibration_preset("aim_speed_focus"))

    assert slider_outcome.cases_evaluated >= 1
    assert split_outcome.cases_evaluated >= 1
    assert slider_outcome.weighted_error >= 0.0
    assert split_outcome.weighted_error >= 0.0
