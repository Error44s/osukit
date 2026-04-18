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
import math
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from .beatmap import Beatmap, Mods
from .difficulty import DifficultyAttributes

if TYPE_CHECKING:
    from .tuning import StdTuningProfile

# Performance Attributes result
@dataclass
class PerformanceAttributes:
    pp: float = 0.0
    pp_aim: float = 0.0
    pp_speed: float = 0.0
    pp_accuracy: float = 0.0
    pp_flashlight: float = 0.0
    effective_miss_count: float = 0.0
    difficulty: DifficultyAttributes = None  # type: ignore[assignment]
    debug: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if self.difficulty is None:
            self.difficulty = DifficultyAttributes()

# Helper utilities
def _logistic(x: float) -> float:
    """Sigmoid / logistic function."""
    return 1.0 / (1.0 + math.exp(-x))


def _ibeta_regularized(a: float, b: float, x: float) -> float:
    """
    Approximation of the regularized incomplete beta function used for
    miss penalty calculation. Uses continued fraction approximation.
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    # Simple numerical approximation via quadrature (good enough for our range)
    # We mainly use this for the miss count estimation
    return x ** a * (1 - x) ** b  # simplified placeholder


def _calculate_effective_miss_count(
    attrs: DifficultyAttributes,
    combo: int,
    misses: int,
    slider_tick_miss: int,
    slider_end_miss: int,
    max_combo: int,
) -> float:
    """Estimate an effective miss count that accounts for slider breaks."""
    combo_based_miss_count = 0.0

    if attrs.slider_count > 0:
        full_combo_threshold = max_combo - 0.1 * attrs.slider_count
        if combo < full_combo_threshold:
            combo_based_miss_count = full_combo_threshold / max(1.0, combo)

    combo_based_miss_count = min(
        combo_based_miss_count,
        float(slider_tick_miss + slider_end_miss + misses)
    )
    return max(float(misses), combo_based_miss_count)


def _miss_penalty(miss_count: float, difficult_strain_count: float) -> float:
    """Penalty multiplier for misses relative to strain count.

    Tuned to be less placeholder-like than the original phase-1 version while still
    remaining conservative.
    """
    if miss_count <= 0:
        return 1.0
    log_term = max(1.0, math.log1p(max(0.0, difficult_strain_count)))
    base = 0.96 ** miss_count
    strain_term = 1.0 / (1.0 + miss_count / (4.0 * log_term))
    return max(0.0, min(1.0, base * strain_term))


def _combo_scaling_factor(combo: int, max_combo: int) -> float:
    if max_combo <= 0:
        return 1.0
    combo = max(0, combo)
    if combo >= max_combo:
        return 1.0
    ratio = combo / max_combo
    return max(0.0, min(1.0, ratio ** 0.8))


def _derive_hitresults(total_hits: int, misses: int, accuracy_percent: float) -> tuple[int, int, int, int]:
    """Derive a plausible hitresult distribution from only accuracy + misses.

    This is still a heuristic, but it is much closer to the target accuracy than the
    old placeholder that defaulted almost everything to 300s.
    """
    total_hits = max(0, int(total_hits))
    misses = max(0, min(int(misses), total_hits))
    remaining = total_hits - misses

    if remaining <= 0:
        return 0, 0, 0, misses

    target_points = round(max(0.0, min(100.0, accuracy_percent)) / 100.0 * 6.0 * total_hits)
    target_points = max(0, min(target_points, 6 * remaining))
    deficit = 6 * remaining - target_points

    best: tuple[int, int, int, int] | None = None
    best_err: tuple[int, int] | None = None

    # Replacing one 300 by a 100 reduces score by 4, by a 50 reduces by 5.
    # Search a compact space for a near-exact distribution.
    max_n50 = min(remaining, deficit // 5 + 2)
    for n50 in range(max_n50 + 1):
        remaining_deficit = deficit - 5 * n50
        if remaining_deficit < 0:
            continue
        n100 = min(remaining - n50, remaining_deficit // 4)
        covered = 4 * n100 + 5 * n50
        leftover = deficit - covered

        if leftover > 0 and n100 + n50 < remaining:
            # Try one more 100 if it improves the match.
            maybe_covered = covered + 4
            maybe_leftover = abs(deficit - maybe_covered)
            if maybe_leftover < abs(leftover):
                n100 += 1
                covered = maybe_covered
                leftover = deficit - covered

        n300 = remaining - n100 - n50
        if n300 < 0:
            continue

        err = (abs(leftover), n50)
        if best_err is None or err < best_err:
            best_err = err
            best = (n300, n100, n50, misses)
            if err == (0, 0):
                break

    if best is None:
        return remaining, 0, 0, misses

    return best


def _hidden_bonus(ar: float) -> float:
    return 1.0 + 0.04 * max(0.0, 12.0 - ar)


def _hd_bonus(ar: float, hit_acc: float, speed_difficulty: float, tuning) -> float:
    ar_component = 1.0 + max(0.0, ar - 9.0) * tuning.hidden_high_ar_weight
    acc_component = math.pow(max(0.0, min(1.0, hit_acc)), tuning.hidden_accuracy_exponent)
    speed_component = 1.0 + max(0.0, speed_difficulty - 2.0) * tuning.hidden_speed_weight
    return _hidden_bonus(ar) * ar_component * acc_component * speed_component


def _dt_speed_bonus(speed_difficulty: float, hit_acc: float, ar: float, tuning) -> tuple[float, float]:
    speed_component = 1.0 + max(0.0, speed_difficulty - 2.5) * tuning.dt_speed_weight
    accuracy_component = 1.0 - (1.0 - max(0.0, min(1.0, hit_acc))) * tuning.dt_accuracy_penalty_weight
    high_ar_component = 1.0 + max(0.0, ar - 10.0) * tuning.dt_high_ar_bonus_weight
    return speed_component * max(0.5, accuracy_component) * high_ar_component, accuracy_component

def _slider_signal(difficulty: DifficultyAttributes, total_hits: int) -> tuple[float, float]:
    if total_hits <= 0 or difficulty.slider_count <= 0:
        return 0.0, 0.0
    slider_ratio = difficulty.slider_count / total_hits
    velocity_signal = max(0.0, 1.0 - difficulty.slider_factor) * slider_ratio
    tail_signal = slider_ratio * (1.0 - min(1.0, difficulty.slider_factor))
    return slider_ratio, max(0.0, velocity_signal + tail_signal)


def _stream_balance(aim_difficulty: float, speed_difficulty: float) -> tuple[float, float]:
    total = max(1e-6, aim_difficulty + speed_difficulty)
    return aim_difficulty / total, speed_difficulty / total


def _length_bonus(total_hits: int) -> float:
    if total_hits <= 0:
        return 1.0
    return 0.95 + 0.4 * min(1.0, total_hits / 2000.0) + (
        math.log10(total_hits / 2000.0) * 0.5 if total_hits > 2000 else 0.0
    )



def _resolve_tuning(tuning: Optional["StdTuningProfile"] = None):
    if tuning is not None:
        return tuning
    from .tuning import DEFAULT_STD_TUNING

    return DEFAULT_STD_TUNING


def _ar_bonus(ar: float, tuning) -> float:
    bonus = 0.0
    if ar > tuning.high_ar_threshold:
        bonus += tuning.high_ar_bonus_factor * (ar - tuning.high_ar_threshold)
    elif ar < tuning.low_ar_threshold:
        bonus += tuning.low_ar_bonus_factor * (tuning.low_ar_threshold - ar)
    return bonus
# Public API: Performance calculator
def calculate_performance(
    beatmap: Beatmap,
    difficulty: Optional[DifficultyAttributes] = None,
    mods: Mods = Mods.NM,
    accuracy: float = 100.0,      # 0-100
    combo: Optional[int] = None,
    misses: int = 0,
    n300: Optional[int] = None,
    n100: Optional[int] = None,
    n50: Optional[int] = None,
    slider_tick_miss: int = 0,
    slider_end_miss: int = 0,
    clock_rate: Optional[float] = None,
    tuning: Optional["StdTuningProfile"] = None,
) -> PerformanceAttributes:
    """
    Calculate performance points for an osu! standard score.

    Parameters
    ----------
    beatmap         : parsed Beatmap object
    difficulty      : pre-calculated DifficultyAttributes (optional, recalculated if None)
    mods            : Mods bitfield
    accuracy        : score accuracy as percentage 0–100 (used if n300/n100/n50 not given)
    combo           : score combo (defaults to full combo)
    misses          : number of misses
    n300            : number of 300s (overrides accuracy)
    n100            : number of 100s (overrides accuracy)
    n50             : number of 50s (overrides accuracy)
    slider_tick_miss: dropped slider ticks
    slider_end_miss : dropped slider ends
    clock_rate      : override clock rate
    """
    from .difficulty import calculate_difficulty

    if difficulty is None:
        difficulty = calculate_difficulty(beatmap, mods=mods, clock_rate=clock_rate)

    tuning = _resolve_tuning(tuning)

    total_hits = difficulty.hit_circle_count + difficulty.slider_count + difficulty.spinner_count
    if total_hits == 0:
        return PerformanceAttributes(difficulty=difficulty)

    max_combo = difficulty.max_combo
    if combo is None:
        combo = max_combo

    # Determine hit counts
    acc_frac = max(0.0, min(100.0, accuracy)) / 100.0
    if n300 is not None:
        _n300 = n300
        _n100 = n100 or 0
        _n50 = n50 or 0
        _n_miss = misses
    else:
        _n300, _n100, _n50, _n_miss = _derive_hitresults(total_hits, misses, accuracy)

    hit_acc = (6.0 * _n300 + 2.0 * _n100 + _n50) / (6.0 * max(1, total_hits))
    hit_acc = max(0.0, min(1.0, hit_acc))

    # Effective miss count
    effective_miss_count = _calculate_effective_miss_count(
        difficulty, combo, misses, slider_tick_miss, slider_end_miss, max_combo
    )

    od = difficulty.overall_difficulty
    ar = difficulty.approach_rate

    # AIM PP
    aim_difficulty = difficulty.aim_difficulty
    raw_aim = math.pow(5.0 * max(1.0, aim_difficulty / 0.0675) - 4.0, 3.0) / 100000.0
    raw_aim *= tuning.aim_multiplier

    # Object count scaling
    total_hits_factor = _length_bonus(total_hits)
    raw_aim *= total_hits_factor * tuning.length_bonus_multiplier

    # AR bonus
    ar_factor = _ar_bonus(ar, tuning)
    raw_aim *= 1.0 + ar_factor

    hd_bonus = 1.0
    # HD bonus
    if mods & Mods.HD:
        hd_bonus = _hd_bonus(ar, hit_acc, difficulty.speed_difficulty, tuning)
        raw_aim *= hd_bonus * tuning.hidden_multiplier * tuning.hidden_bonus_multiplier

    # FL bonus
    if mods & Mods.FL:
        raw_aim *= 1.0 + 0.35 * min(1.0, total_hits / 200.0) + (
            0.3 * min(1.0, (total_hits - 200) / 300.0) if total_hits > 200 else 0.0
        ) + (
            (total_hits - 500) / 1200.0 if total_hits > 500 else 0.0
        )

    # Accuracy scaling
    raw_aim *= 0.5 + hit_acc / 2.0
    raw_aim *= 0.98 + od * od / 2500.0
    raw_aim *= tuning.aim_accuracy_multiplier

    # Miss penalty
    if effective_miss_count > 0:
        raw_aim *= _miss_penalty(effective_miss_count, difficulty.aim_difficult_strain_count)

    # Combo scaling
    combo_scaling = _combo_scaling_factor(combo, max_combo)
    raw_aim *= combo_scaling ** tuning.combo_exponent

    # Slider nerf / slider-heavy shaping
    estimate_improper_sliders = 0.0
    slider_ratio, slider_signal = _slider_signal(difficulty, total_hits)
    slider_velocity_bonus = 1.0
    slider_head_bonus = 1.0
    slider_tail_bonus = 1.0
    if difficulty.slider_count > 0:
        estimate_improper_sliders = min(
            float(slider_end_miss + misses),
            float(difficulty.slider_count)
        )
        improper_ratio = estimate_improper_sliders / difficulty.slider_count
        slider_nerf = (1.0 - difficulty.slider_factor) * math.pow(
            max(0.0, 1.0 - improper_ratio * tuning.slider_miss_weight), tuning.slider_nerf_exponent
        ) + difficulty.slider_factor
        raw_aim *= slider_nerf
        slider_velocity_bonus = 1.0 + slider_signal * tuning.slider_velocity_weight
        slider_head_bonus = 1.0 + slider_ratio * tuning.slider_head_weight * max(0.0, difficulty.aim_difficulty - difficulty.speed_difficulty)
        slider_tail_bonus = 1.0 + slider_signal * tuning.slider_tail_weight
        raw_aim *= slider_velocity_bonus * slider_head_bonus * slider_tail_bonus

    aim_share, speed_share = _stream_balance(aim_difficulty, difficulty.speed_difficulty)
    aim_stream_bonus = 1.0 + max(0.0, aim_share - 0.5) * tuning.aim_stream_balance
    raw_aim *= aim_stream_bonus

    pp_aim = raw_aim

    # SPEED PP
    speed_difficulty = difficulty.speed_difficulty
    raw_speed = math.pow(5.0 * max(1.0, speed_difficulty / 0.0675) - 4.0, 3.0) / 100000.0
    raw_speed *= tuning.speed_multiplier

    raw_speed *= total_hits_factor * tuning.length_bonus_multiplier

    # AR bonus for speed
    if ar > tuning.high_ar_threshold:
        raw_speed *= 1.0 + tuning.high_ar_bonus_factor * (ar - tuning.high_ar_threshold)

    speed_hd_bonus = 1.0
    # HD bonus for speed
    if mods & Mods.HD:
        speed_hd_bonus = _hd_bonus(ar, hit_acc, speed_difficulty, tuning)
        raw_speed *= speed_hd_bonus * tuning.hidden_multiplier * tuning.hidden_bonus_multiplier

    dt_speed_bonus = 1.0
    dt_accuracy_component = 1.0
    if mods & Mods.DT:
        dt_speed_bonus, dt_accuracy_component = _dt_speed_bonus(speed_difficulty, hit_acc, ar, tuning)
        raw_speed *= dt_speed_bonus

    # Accuracy scaling (speed is sensitive to accuracy)
    speed_acc = math.pow(
        max(0.0, min(1.0, (hit_acc + _relevantAccuracy(hit_acc, od)) / 2.0)),
        (14.5 - max(od, 8.0)) / 2.0,
    )
    raw_speed *= speed_acc * tuning.speed_accuracy_multiplier

    # 50s punishment
    n50_fraction = _n50 / max(1, total_hits)
    raw_speed *= math.pow(0.98, max(0.0, (_n50 - total_hits / 500.0) * tuning.speed_n50_penalty_scale))
    raw_speed *= max(tuning.speed_n50_floor, 1.0 - n50_fraction * 0.25 * tuning.speed_n50_penalty_scale)

    # Miss penalty
    if effective_miss_count > 0:
        raw_speed *= _miss_penalty(effective_miss_count, difficulty.speed_difficult_strain_count)

    # Combo scaling
    raw_speed *= combo_scaling ** tuning.combo_exponent

    speed_stream_bonus = 1.0 + max(0.0, speed_share - 0.5) * tuning.speed_stream_balance
    slider_speed_penalty = 1.0 - min(0.2, slider_ratio * tuning.slider_velocity_weight * 0.5)
    raw_speed *= speed_stream_bonus * slider_speed_penalty

    pp_speed = raw_speed

    accuracy_hd_bonus = 1.0

    # ACCURACY PP
    # Only hit circles count for accuracy
    n_circles = difficulty.hit_circle_count
    better_acc = 0.0
    if n_circles > 0:
        better_acc = max(
            0.0,
            ((_n300 - max(total_hits - n_circles, 0)) * 6.0 + _n100 * 2.0 + _n50) /
            (n_circles * 6.0)
        )

    raw_acc = math.pow(1.52163, od) * math.pow(better_acc, tuning.accuracy_exponent) * 2.83
    raw_acc *= tuning.accuracy_multiplier

    # Scaling by object count
    raw_acc *= min(1.15, math.pow(n_circles / 1000.0, tuning.accuracy_circle_exponent))

    # Mod bonuses
    accuracy_hd_bonus = 1.0
    if mods & Mods.HD:
        accuracy_hd_bonus = 1.02 + max(0.0, ar - 9.0) * (tuning.hidden_high_ar_weight * 0.5)
        accuracy_hd_bonus *= math.pow(max(0.0, min(1.0, better_acc or hit_acc)), max(0.5, tuning.hidden_accuracy_exponent * 0.5))
        raw_acc *= accuracy_hd_bonus
    if mods & Mods.FL:
        raw_acc *= 1.02
    if mods & Mods.DT:
        raw_acc *= max(0.75, dt_accuracy_component)

    pp_accuracy = raw_acc

    # FLASHLIGHT PP
    pp_flashlight = 0.0
    if mods & Mods.FL:
        fl_difficulty = difficulty.flashlight_difficulty
        raw_fl = math.pow(fl_difficulty, 2.0) * 25.0
        # Object count scaling
        raw_fl *= 0.7 + 0.1 * min(1.0, total_hits / 200.0) + (
            0.2 * min(1.0, (total_hits - 200) / 200.0) if total_hits > 200 else 0.0
        )
        # Accuracy scaling
        raw_fl *= 0.5 + hit_acc / 2.0
        raw_fl *= 0.98 + od * od / 2500.0
        if effective_miss_count > 0:
            raw_fl *= _miss_penalty(effective_miss_count, difficulty.aim_difficult_strain_count)
        pp_flashlight = raw_fl * tuning.flashlight_multiplier

    # COMBINE
    base_pp = math.pow(
        math.pow(pp_aim, 1.1)
        + math.pow(pp_speed, 1.1)
        + math.pow(pp_accuracy, 1.1)
        + math.pow(pp_flashlight, 1.1),
        1.0 / 1.1,
    )

    base_pp *= tuning.final_multiplier

    # NF nerf
    if mods & Mods.NF:
        base_pp *= max(0.90, 1.0 - 0.02 * effective_miss_count)

    # SO nerf (SpunOut)
    if mods & Mods.SO:
        base_pp *= 1.0 - math.pow(float(difficulty.spinner_count) / total_hits, 0.85)

    # RX nerf (Relax)
    if mods & Mods.RX:
        rx_pp_aim = pp_aim * 0.9
        rx_pp_speed = pp_speed * 0.3
        rx_pp_acc = pp_accuracy * 0.8
        base_pp = math.pow(
            math.pow(rx_pp_aim, 1.1)
            + math.pow(rx_pp_speed, 1.1)
            + math.pow(rx_pp_acc, 1.1)
            + math.pow(pp_flashlight, 1.1),
            1.0 / 1.1,
        ) * 0.9

    return PerformanceAttributes(
        pp=max(0.0, base_pp),
        pp_aim=max(0.0, pp_aim),
        pp_speed=max(0.0, pp_speed),
        pp_accuracy=max(0.0, pp_accuracy),
        pp_flashlight=max(0.0, pp_flashlight),
        effective_miss_count=effective_miss_count,
        difficulty=difficulty,
        debug={
            "accuracy_fraction": hit_acc,
            "better_accuracy_fraction": better_acc,
            "length_bonus": total_hits_factor,
            "combo_scaling": combo_scaling,
            "tuning_aim_multiplier": tuning.aim_multiplier,
            "tuning_speed_multiplier": tuning.speed_multiplier,
            "tuning_accuracy_multiplier": tuning.accuracy_multiplier,
            "tuning_combo_exponent": tuning.combo_exponent,
            "tuning_final_multiplier": tuning.final_multiplier,
            "tuning_length_bonus_multiplier": tuning.length_bonus_multiplier,
            "tuning_hidden_bonus_multiplier": tuning.hidden_bonus_multiplier,
            "tuning_slider_nerf_exponent": tuning.slider_nerf_exponent,
            "tuning_slider_miss_weight": tuning.slider_miss_weight,
            "tuning_speed_n50_penalty_scale": tuning.speed_n50_penalty_scale,
            "tuning_flashlight_multiplier": tuning.flashlight_multiplier,
            "miss_penalty_aim": _miss_penalty(effective_miss_count, difficulty.aim_difficult_strain_count),
            "miss_penalty_speed": _miss_penalty(effective_miss_count, difficulty.speed_difficult_strain_count),
            "n300": float(_n300),
            "n100": float(_n100),
            "n50": float(_n50),
            "n_miss": float(_n_miss),
            "hd_bonus_aim": hd_bonus,
            "hd_bonus_speed": speed_hd_bonus,
            "dt_speed_bonus": dt_speed_bonus,
            "dt_accuracy_component": dt_accuracy_component,
            "accuracy_hd_bonus": accuracy_hd_bonus,
            "slider_ratio": slider_ratio,
            "slider_signal": slider_signal,
            "slider_velocity_bonus": slider_velocity_bonus,
            "slider_head_bonus": slider_head_bonus,
            "slider_tail_bonus": slider_tail_bonus,
            "aim_stream_bonus": aim_stream_bonus,
            "speed_stream_bonus": speed_stream_bonus,
            "tuning_slider_velocity_weight": tuning.slider_velocity_weight,
            "tuning_slider_head_weight": tuning.slider_head_weight,
            "tuning_slider_tail_weight": tuning.slider_tail_weight,
            "tuning_aim_stream_balance": tuning.aim_stream_balance,
            "tuning_speed_stream_balance": tuning.speed_stream_balance,
            "tuning_hidden_high_ar_weight": tuning.hidden_high_ar_weight,
            "tuning_hidden_accuracy_exponent": tuning.hidden_accuracy_exponent,
            "tuning_hidden_speed_weight": tuning.hidden_speed_weight,
            "tuning_dt_speed_weight": tuning.dt_speed_weight,
            "tuning_dt_accuracy_penalty_weight": tuning.dt_accuracy_penalty_weight,
            "tuning_dt_high_ar_bonus_weight": tuning.dt_high_ar_bonus_weight,
        },
    )


def _relevantAccuracy(hit_acc: float, od: float) -> float:
    """Speed-relevant accuracy (from osu!lazer)."""
    # Clamp OD to avoid extreme values
    od_clamped = max(0.0, min(10.0, od))
    return max(0.0, hit_acc * (14.5 - od_clamped) / 2.0 - max(0.0, (14.5 - od_clamped) / 2.0 - 1.0))
