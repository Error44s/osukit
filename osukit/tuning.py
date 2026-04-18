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

from dataclasses import dataclass, asdict, field
from itertools import product
from typing import Literal
from typing import Sequence


@dataclass(frozen=True)
class StdTuningProfile:
    aim_multiplier: float = 1.0
    speed_multiplier: float = 1.0
    accuracy_multiplier: float = 1.0
    hidden_multiplier: float = 1.0
    flashlight_multiplier: float = 1.0
    aim_accuracy_multiplier: float = 1.0
    speed_accuracy_multiplier: float = 1.0
    combo_exponent: float = 1.0
    accuracy_exponent: float = 24.0
    final_multiplier: float = 1.0
    length_bonus_multiplier: float = 1.0
    hidden_bonus_multiplier: float = 1.0
    slider_nerf_exponent: float = 3.0
    slider_miss_weight: float = 1.0
    speed_n50_penalty_scale: float = 1.0
    speed_n50_floor: float = 0.75
    accuracy_circle_exponent: float = 0.3
    high_ar_threshold: float = 10.33
    low_ar_threshold: float = 8.0
    high_ar_bonus_factor: float = 0.3
    low_ar_bonus_factor: float = 0.01
    hidden_high_ar_weight: float = 0.05
    hidden_accuracy_exponent: float = 1.5
    hidden_speed_weight: float = 0.02
    dt_speed_weight: float = 0.025
    dt_accuracy_penalty_weight: float = 0.5
    dt_high_ar_bonus_weight: float = 0.04
    slider_velocity_weight: float = 0.08
    slider_head_weight: float = 0.06
    slider_tail_weight: float = 0.05
    aim_stream_balance: float = 0.05
    speed_stream_balance: float = 0.05

    def with_updates(self, **updates) -> "StdTuningProfile":
        data = asdict(self)
        data.update(updates)
        return StdTuningProfile(**data)


DEFAULT_STD_TUNING = StdTuningProfile()


@dataclass
class CalibrationObjective:
    tag_weights: dict[str, float] = field(default_factory=dict)
    metric_weights: dict[str, float] = field(default_factory=dict)



@dataclass(frozen=True)
class CalibrationPreset:
    name: str
    objective: CalibrationObjective
    search_scale: float = 0.04


def build_calibration_preset(name: str) -> CalibrationPreset:
    key = name.lower().strip()
    presets = {
        "balanced": CalibrationPreset(
            name="balanced",
            objective=CalibrationObjective(),
            search_scale=0.04,
        ),
        "hd_focus": CalibrationPreset(
            name="hd_focus",
            objective=CalibrationObjective(tag_weights={"hd": 2.5, "aim": 1.25}, metric_weights={"performance.pp": 2.0, "performance.accuracy": 1.25}),
            search_scale=0.03,
        ),
        "dt_focus": CalibrationPreset(
            name="dt_focus",
            objective=CalibrationObjective(tag_weights={"dt": 2.5, "speed": 1.5}, metric_weights={"performance.pp": 2.0, "performance.speed": 1.5, "difficulty.speed": 1.2}),
            search_scale=0.03,
        ),
        "slider_focus": CalibrationPreset(
            name="slider_focus",
            objective=CalibrationObjective(tag_weights={"slider-heavy": 3.0, "long": 1.2}, metric_weights={"performance.pp": 2.0, "difficulty.stars": 1.25, "performance.aim": 1.25}),
            search_scale=0.025,
        ),
        "aim_speed_focus": CalibrationPreset(
            name="aim_speed_focus",
            objective=CalibrationObjective(tag_weights={"aim": 1.6, "speed": 1.6, "stream": 1.25}, metric_weights={"performance.aim": 1.7, "performance.speed": 1.7, "performance.pp": 1.3}),
            search_scale=0.025,
        ),
        "accuracy_focus": CalibrationPreset(
            name="accuracy_focus",
            objective=CalibrationObjective(tag_weights={"accuracy": 2.5}, metric_weights={"performance.accuracy": 2.5, "performance.pp": 1.5}),
            search_scale=0.025,
        ),
    }
    if key not in presets:
        raise ValueError(f"Unknown calibration preset: {name!r}")
    return presets[key]


def optimize_with_preset(cases: Sequence, preset: str | CalibrationPreset):
    if isinstance(preset, str):
        preset = build_calibration_preset(preset)
    return optimize_standard_tuning(cases, search_scale=preset.search_scale, objective=preset.objective)

@dataclass
class CalibrationOutcome:
    tuning: StdTuningProfile
    average_relative_error: float
    max_relative_error: float
    cases_evaluated: int
    weighted_error: float = 0.0


def score_suite(report, objective: CalibrationObjective | None = None) -> tuple[float, float, int, float]:
    rel_errors: list[float] = []
    weighted_errors: list[float] = []
    weighted_denominator = 0.0
    objective = objective or CalibrationObjective()

    for result in report.results:
        tags = getattr(result, "tags", [])
        tag_weight = max([objective.tag_weights.get(tag, 1.0) for tag in tags], default=1.0)
        for check in [*result.difficulty_checks, *result.performance_checks]:
            error = abs(check.relative_error)
            rel_errors.append(error)
            metric_weight = objective.metric_weights.get(check.metric, 1.0)
            weight = tag_weight * metric_weight
            weighted_errors.append(error * weight)
            weighted_denominator += weight

    if not rel_errors:
        return 0.0, 0.0, 0, 0.0

    weighted_error = sum(weighted_errors) / weighted_denominator if weighted_denominator > 0 else 0.0
    return sum(rel_errors) / len(rel_errors), max(rel_errors), len(rel_errors), weighted_error


def optimize_standard_tuning(
    cases: Sequence,
    *,
    search_scale: float = 0.04,
    objective: CalibrationObjective | None = None,
):
    """Simple grid-search tuner for std PP golden cases.

    This is intentionally conservative: it nudges a few high-level multipliers
    so developers can calibrate against external reference values without hand-editing
    constants all over the engine.
    """
    from .benchmark import run_golden_suite

    offsets = (-search_scale, 0.0, search_scale)
    best = DEFAULT_STD_TUNING
    base_report = run_golden_suite(cases, tuning=best)
    best_avg, best_max, evaluated, best_weighted = score_suite(base_report, objective)

    for aim_off, speed_off, acc_off, final_off in product(offsets, repeat=4):
        candidate = DEFAULT_STD_TUNING.with_updates(
            aim_multiplier=1.0 + aim_off,
            speed_multiplier=1.0 + speed_off,
            accuracy_multiplier=1.0 + acc_off,
            final_multiplier=1.0 + final_off,
        )
        report = run_golden_suite(cases, tuning=candidate)
        avg, max_err, _, weighted = score_suite(report, objective)
        if (weighted, avg, max_err) < (best_weighted, best_avg, best_max):
            best = candidate
            best_avg = avg
            best_max = max_err
            best_weighted = weighted

    secondary_offsets = (-search_scale / 2.0, 0.0, search_scale / 2.0)
    for hidden_off, slider_off, n50_off, length_off in product(secondary_offsets, repeat=4):
        candidate = best.with_updates(
            hidden_bonus_multiplier=max(0.8, best.hidden_bonus_multiplier + hidden_off),
            slider_nerf_exponent=max(1.0, best.slider_nerf_exponent + slider_off * 10.0),
            speed_n50_penalty_scale=max(0.5, best.speed_n50_penalty_scale + n50_off * 2.0),
            length_bonus_multiplier=max(0.7, best.length_bonus_multiplier + length_off),
        )
        report = run_golden_suite(cases, tuning=candidate)
        avg, max_err, _, weighted = score_suite(report, objective)
        if (weighted, avg, max_err) < (best_weighted, best_avg, best_max):
            best = candidate
            best_avg = avg
            best_max = max_err
            best_weighted = weighted

    mod_offsets = (-search_scale / 3.0, 0.0, search_scale / 3.0)
    for hd_off, dt_off, acc_off, high_ar_off in product(mod_offsets, repeat=4):
        candidate = best.with_updates(
            hidden_high_ar_weight=max(0.0, best.hidden_high_ar_weight + hd_off),
            dt_speed_weight=max(0.0, best.dt_speed_weight + dt_off),
            dt_accuracy_penalty_weight=max(0.1, best.dt_accuracy_penalty_weight + acc_off),
            dt_high_ar_bonus_weight=max(0.0, best.dt_high_ar_bonus_weight + high_ar_off),
        )
        report = run_golden_suite(cases, tuning=candidate)
        avg, max_err, _, weighted = score_suite(report, objective)
        if (weighted, avg, max_err) < (best_weighted, best_avg, best_max):
            best = candidate
            best_avg = avg
            best_max = max_err
            best_weighted = weighted

    split_offsets = (-search_scale / 4.0, 0.0, search_scale / 4.0)
    for slider_off, head_off, tail_off, aim_off, speed_off in product(split_offsets, repeat=5):
        candidate = best.with_updates(
            slider_velocity_weight=max(0.0, best.slider_velocity_weight + slider_off),
            slider_head_weight=max(0.0, best.slider_head_weight + head_off),
            slider_tail_weight=max(0.0, best.slider_tail_weight + tail_off),
            aim_stream_balance=max(0.0, best.aim_stream_balance + aim_off),
            speed_stream_balance=max(0.0, best.speed_stream_balance + speed_off),
        )
        report = run_golden_suite(cases, tuning=candidate)
        avg, max_err, _, weighted = score_suite(report, objective)
        if (weighted, avg, max_err) < (best_weighted, best_avg, best_max):
            best = candidate
            best_avg = avg
            best_max = max_err
            best_weighted = weighted

    return CalibrationOutcome(
        tuning=best,
        average_relative_error=best_avg,
        max_relative_error=best_max,
        cases_evaluated=evaluated,
        weighted_error=best_weighted,
    )




def build_candidate_profiles(base: StdTuningProfile | None = None) -> dict[str, StdTuningProfile]:
    base = base or DEFAULT_STD_TUNING
    return {
        'default': base,
        'hd_candidate': base.with_updates(hidden_bonus_multiplier=base.hidden_bonus_multiplier * 1.03, hidden_multiplier=base.hidden_multiplier * 1.01, hidden_high_ar_weight=base.hidden_high_ar_weight * 1.05),
        'dt_candidate': base.with_updates(speed_multiplier=base.speed_multiplier * 1.02, high_ar_bonus_factor=base.high_ar_bonus_factor * 1.03, dt_speed_weight=base.dt_speed_weight * 1.04),
        'slider_candidate': base.with_updates(slider_nerf_exponent=max(1.0, base.slider_nerf_exponent - 0.15), slider_miss_weight=base.slider_miss_weight * 1.03, slider_velocity_weight=base.slider_velocity_weight * 1.12),
        'accuracy_candidate': base.with_updates(accuracy_multiplier=base.accuracy_multiplier * 1.01, accuracy_exponent=base.accuracy_exponent * 0.995),
        'aim_speed_candidate': base.with_updates(aim_stream_balance=base.aim_stream_balance * 1.15, speed_stream_balance=base.speed_stream_balance * 1.15),
    }


__all__ = [
    "StdTuningProfile",
    "DEFAULT_STD_TUNING",
    "CalibrationObjective",
    "CalibrationOutcome",
    "CalibrationPreset",
    "build_calibration_preset",
    "score_suite",
    "optimize_standard_tuning",
    "optimize_with_preset",
    "build_candidate_profiles",
]
