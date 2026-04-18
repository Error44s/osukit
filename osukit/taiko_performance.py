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
from dataclasses import dataclass
from typing import Optional

from .beatmap import Beatmap, Mods
from .taiko_difficulty import TaikoDifficultyAttributes, calculate_taiko_difficulty

# Taiko Performance Attributes
@dataclass
class TaikoPerformanceAttributes:
    pp: float = 0.0
    pp_difficulty: float = 0.0
    pp_accuracy: float = 0.0
    effective_miss_count: float = 0.0
    estimated_unstable_rate: float = 0.0
    difficulty: TaikoDifficultyAttributes = None  # type: ignore

    def __post_init__(self):
        if self.difficulty is None:
            self.difficulty = TaikoDifficultyAttributes()

# Helpers
def _taiko_hit_window_great(od: float) -> float:
    """Hit window for a 300 in Taiko (ms), NOT scaled by clock rate yet."""
    return 80.0 - 6.0 * od


def _estimate_unstable_rate(
    n300: int,
    n100: int,
    n_miss: int,
    great_window: float,
) -> float:
    """
    Estimate unstable rate (UR) from hit counts using a simplified
    normal-distribution approach.
    UR is in osu! units = 10 * standard_deviation_ms.
    """
    total = n300 + n100 + n_miss
    if total == 0:
        return 0.0

    # Simplified: scale from accuracy deviation
    # Perfect 100% → UR = 0; each 100 roughly adds UR
    # Real formula uses inverse error function; we use an approximation
    acc = n300 / total if total > 0 else 1.0

    if acc >= 1.0:
        return 0.0

    # Rough approximation: UR ≈ hitwindow * sqrt(-2 * ln(acc_fraction))
    # clamped to reasonable range
    frac = max(1e-6, acc)
    dev = great_window * math.sqrt(-2.0 * math.log(frac)) * 0.5
    return max(0.0, min(dev * 10.0, 1000.0))


def _miss_penalty(miss_count: float, total_hits: int) -> float:
    """Multiply PP by this for misses."""
    if miss_count == 0 or total_hits == 0:
        return 1.0
    return math.pow(0.985, miss_count)


def _combo_scaling(combo: int, max_combo: int) -> float:
    if max_combo <= 0:
        return 1.0
    return min(math.sqrt(combo) / math.sqrt(max_combo), 1.0)

# Public API
def calculate_taiko_performance(
    beatmap: Beatmap,
    difficulty: Optional[TaikoDifficultyAttributes] = None,
    mods: Mods = Mods.NM,
    accuracy: float = 100.0,
    combo: Optional[int] = None,
    misses: int = 0,
    n300: Optional[int] = None,
    n100: Optional[int] = None,
    clock_rate: Optional[float] = None,
    od_override: Optional[float] = None,
) -> TaikoPerformanceAttributes:
    """
    Calculate performance points for a Taiko score.

    Parameters
    ----------
    beatmap     : parsed Beatmap
    difficulty  : pre-calculated TaikoDifficultyAttributes (optional)
    mods        : Mods bitfield
    accuracy    : score accuracy 0–100 (used if n300/n100 not given)
    combo       : achieved combo (defaults to full combo)
    misses      : number of misses
    n300        : number of greats (overrides accuracy)
    n100        : number of oks   (overrides accuracy)
    clock_rate  : clock rate override
    od_override : OD override
    """
    if difficulty is None:
        difficulty = calculate_taiko_difficulty(
            beatmap, mods=mods, clock_rate=clock_rate, od_override=od_override
        )

    cr = clock_rate if clock_rate is not None else mods.speed_multiplier
    total_hits = difficulty.max_combo
    if total_hits == 0:
        return TaikoPerformanceAttributes(difficulty=difficulty)

    max_combo = total_hits
    if combo is None:
        combo = max_combo

    # Derive hit counts from accuracy if not given explicitly
    acc_frac = max(0.0, min(100.0, accuracy)) / 100.0
    if n300 is not None:
        _n300 = n300
        _n100 = n100 if n100 is not None else max(0, total_hits - n300 - misses)
        _n_miss = misses
    else:
        _n_miss = misses
        remaining = max(0, total_hits - _n_miss)
        # acc = (2*n300 + n100) / (2 * total_hits)   [taiko: 300=1.0, 100=0.5]
        # n300 + n100 = remaining
        # → n300 = 2*acc*total - n100  and n100 = remaining - n300
        # solve: n300 = (2*acc*total - remaining) / 1
        target_points = acc_frac * 2.0 * total_hits
        _n300 = max(0, min(remaining, int(round(target_points - remaining))))
        _n100 = max(0, remaining - _n300)

    # Recalculate effective accuracy
    hit_acc = (2.0 * _n300 + _n100) / (2.0 * max(1, total_hits))
    hit_acc = max(0.0, min(1.0, hit_acc))

    # Effective miss count
    effective_miss_count = max(float(misses), _calculate_effective_miss_count(
        difficulty, combo, misses, max_combo
    ))

    # Great hit window
    od = difficulty.overall_difficulty
    great_window = difficulty.great_hit_window  # already clock-rate-adjusted

    # Estimated unstable rate
    eur = _estimate_unstable_rate(_n300, _n100, _n_miss, great_window)

    # Difficulty PP (Strain)
    star_rating = difficulty.stars
    raw_diff = math.pow(max(1.0, star_rating / 0.0075) * 5.0 - 4.0, 2.0) / 100000.0

    # Length bonus
    length_bonus = min(1.0, total_hits / 1500.0) * 0.1 + 1.0
    raw_diff *= length_bonus

    # Miss penalty
    raw_diff *= _miss_penalty(effective_miss_count, total_hits)

    # Combo scaling
    raw_diff *= _combo_scaling(combo, max_combo)

    # HD bonus
    if mods & Mods.HD:
        raw_diff *= 1.025

    # FL bonus
    if mods & Mods.FL:
        raw_diff *= 1.05 * length_bonus

    # Accuracy multiplier for difficulty pp
    raw_diff *= hit_acc

    pp_difficulty = raw_diff

    # Accuracy PP
    # Based on hit window (OD-dependent)
    raw_acc = math.pow(150.0 / max(1.0, great_window), 1.1)
    raw_acc *= math.pow(hit_acc, 15.0) * 22.0

    # Length bonus
    raw_acc *= min(1.15, math.pow(total_hits / 1500.0, 0.3))

    # HD/FL bonuses
    if mods & Mods.HD:
        raw_acc *= 1.10
    if mods & Mods.FL:
        raw_acc *= 1.025

    # UR-based penalty: punish high UR (inaccurate hits)
    if eur > 0:
        ur_penalty = max(0.0, 1.0 - math.pow(eur / (great_window * 3.0), 0.75))
        raw_acc *= ur_penalty

    pp_accuracy = raw_acc

    # Combine
    base_pp = math.pow(
        math.pow(pp_difficulty, 1.1) + math.pow(pp_accuracy, 1.1),
        1.0 / 1.1,
    )

    # NF nerf
    if mods & Mods.NF:
        base_pp *= max(0.90, 1.0 - 0.02 * effective_miss_count)

    # HT nerf (half time already handled via clock rate, but add tiny penalty)
    if mods & Mods.HT:
        base_pp *= 0.985

    return TaikoPerformanceAttributes(
        pp=max(0.0, base_pp),
        pp_difficulty=max(0.0, pp_difficulty),
        pp_accuracy=max(0.0, pp_accuracy),
        effective_miss_count=effective_miss_count,
        estimated_unstable_rate=eur,
        difficulty=difficulty,
    )


def _calculate_effective_miss_count(
    attrs: TaikoDifficultyAttributes,
    combo: int,
    misses: int,
    max_combo: int,
) -> float:
    if max_combo == 0:
        return float(misses)
    combo_based = 0.0
    if combo < max_combo:
        combo_based = max_combo / max(1.0, combo)
    return max(float(misses), min(combo_based, float(misses + 0.5)))
