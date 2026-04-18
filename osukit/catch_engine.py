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
from typing import Sequence

from .beatmap import Beatmap as CoreBeatmap, Slider, Spinner, HitCircle
from .models import ScoreStatistics


# Difficulty Attributes
@dataclass
class CatchDifficultyAttributes:
    stars: float
    ar: float
    n_fruits: int
    n_droplets: int
    n_tiny_droplets: int
    max_combo: int
    hyper_dash_count: int = 0
    approach_rate_effective: float = 0.0

    @property
    def total_catchable_objects(self) -> int:
        return self.n_fruits + self.n_droplets + self.n_tiny_droplets


@dataclass
class CatchPerformanceAttributes:
    pp: float
    difficulty: CatchDifficultyAttributes
    accuracy: float
    combo_ratio: float

    @property
    def stars(self) -> float:
        return self.difficulty.stars

# Difficulty calculation
def _effective_ar(ar: float, mods_int: int = 0) -> float:
    from .beatmap import Mods
    mods = Mods(mods_int)
    ar_adj = ar * mods.ar_multiplier
    ar_adj = max(0.0, min(10.0, ar_adj))
    if mods.speed_multiplier != 1.0:
        # Convert AR to ms, apply speed, convert back
        if ar_adj <= 5:
            ms = 1800.0 - 120.0 * ar_adj
        else:
            ms = 1200.0 - 150.0 * (ar_adj - 5.0)
        ms /= mods.speed_multiplier
        if ms >= 1200:
            ar_adj = (1800.0 - ms) / 120.0
        else:
            ar_adj = 5.0 + (1200.0 - ms) / 150.0
    return max(0.0, min(10.0, ar_adj))


def _count_hyper_dashes(bm: CoreBeatmap, cs: float) -> int:
    """Rough hyper dash count: count sliders where next object requires hyper dash."""
    circle_size_px = 54.4 - 4.48 * cs
    catch_width = circle_size_px * 2.0
    count = 0
    objects = [obj for obj in bm.hit_objects if not isinstance(obj, Spinner)]
    for i in range(len(objects) - 1):
        curr = objects[i]
        nxt = objects[i + 1]
        curr_x = getattr(curr, 'pos', None)
        nxt_x = getattr(nxt, 'pos', None)
        if curr_x is None or nxt_x is None:
            continue
        dt = float(getattr(nxt, 'time', 0)) - float(getattr(curr, 'end_time', getattr(curr, 'time', 0)))
        if dt <= 0:
            continue
        dist = abs(nxt_x.x - curr_x.x)
        speed_needed = dist / dt * 1000.0
        # Rough catcher speed limit
        catcher_speed = 505.0 * (1.0 + 0.5 * cs / 10.0)
        if speed_needed > catcher_speed:
            count += 1
    return count


def calculate_catch_difficulty(bm: CoreBeatmap, mods_int: int = 0) -> CatchDifficultyAttributes:
    """
    Local catch difficulty approximation.
    Inspired by the official algorithm structure but simplified.
    """
    from .beatmap import Mods
    mods = Mods(mods_int)
    cs = max(0.0, min(10.0, bm.cs * mods.cs_multiplier))
    ar = _effective_ar(bm.ar, mods_int)

    n_fruits = sum(1 for o in bm.hit_objects if isinstance(o, HitCircle))
    n_sliders = sum(1 for o in bm.hit_objects if isinstance(o, Slider))
    n_spinners = sum(1 for o in bm.hit_objects if isinstance(o, Spinner))

    # Count slider ticks as droplets
    n_droplets = sum(getattr(o, 'tick_count', 0) for o in bm.hit_objects if isinstance(o, Slider))
    # Slider ends as tiny droplets
    n_tiny_droplets = n_sliders

    max_combo = n_fruits + n_droplets + n_tiny_droplets

    hyper_dashes = _count_hyper_dashes(bm, cs)

    # Approximate star rating
    # Based on: object density, AR, CS, hyper dash ratio
    if not bm.hit_objects:
        return CatchDifficultyAttributes(
            stars=0.0, ar=ar, n_fruits=n_fruits, n_droplets=n_droplets,
            n_tiny_droplets=n_tiny_droplets, max_combo=max_combo,
        )

    total_objs = len(bm.hit_objects)
    duration_s = max(1.0, (
        float(getattr(bm.hit_objects[-1], 'end_time', getattr(bm.hit_objects[-1], 'time', 0)))
        - float(getattr(bm.hit_objects[0], 'time', 0))
    ) / 1000.0)
    obj_density = total_objs / duration_s

    # Hyper dash penalty adds difficulty
    hyper_ratio = hyper_dashes / max(1, n_fruits + n_sliders)

    # CS affects how tight the catching window is
    cs_factor = 1.0 + (cs - 5.0) * 0.04

    # AR affects reading difficulty
    ar_factor = 1.0 + max(0.0, ar - 8.0) * 0.05

    base_stars = (
        0.35 * obj_density
        + 1.2 * hyper_ratio
        + ar_factor * 0.3
    ) * cs_factor * mods.speed_multiplier

    stars = round(max(0.0, base_stars), 4)

    return CatchDifficultyAttributes(
        stars=stars,
        ar=ar,
        n_fruits=n_fruits,
        n_droplets=n_droplets,
        n_tiny_droplets=n_tiny_droplets,
        max_combo=max_combo,
        hyper_dash_count=hyper_dashes,
        approach_rate_effective=ar,
    )


# Performance calculation
def calculate_catch_performance(
    difficulty: CatchDifficultyAttributes,
    statistics: ScoreStatistics,
    combo: int,
    mods_int: int = 0,
    passed: bool = True,
    object_index: int | None = None,
) -> CatchPerformanceAttributes:
    """
    Local catch PP approximation.

    Formula modeled after the official Lazer catch pp formula structure.
    """
    stars = difficulty.stars
    if stars <= 0 or difficulty.max_combo <= 0:
        return CatchPerformanceAttributes(pp=0.0, difficulty=difficulty, accuracy=0.0, combo_ratio=0.0)

    # Accuracy: (fruits + droplets + tiny) caught vs total
    total_catchable = difficulty.total_catchable_objects
    caught = statistics.count_300 + statistics.count_100 + statistics.count_50
    accuracy = max(0.0, min(1.0, caught / max(1, total_catchable)))

    combo_ratio = min(1.0, combo / max(1, difficulty.max_combo))

    # Base pp value
    base = ((5.0 * stars / 0.0049) - 4.0) ** 2.0 / 100000.0

    # Length bonus
    length_bonus = 0.95 + 0.3 * math.log(1.0 + difficulty.n_fruits / 2500.0, 10)
    if difficulty.n_fruits > 3000:
        length_bonus += math.log(difficulty.n_fruits / 3000.0, 10) * 0.5

    # Miss penalty
    miss_penalty = 0.97 ** statistics.count_miss

    # Combo break penalty
    combo_penalty = min(1.0, (combo / difficulty.max_combo) ** 0.8)

    # AR bonus
    ar_bonus = 1.0
    if difficulty.ar > 9.0:
        ar_bonus += 0.1 * (difficulty.ar - 9.0)
    if difficulty.ar > 10.0:
        ar_bonus += 0.1 * (difficulty.ar - 10.0)
    elif difficulty.ar < 8.0:
        ar_bonus += 0.025 * (8.0 - difficulty.ar)

    # Accuracy bonus (strong penalty for low accuracy)
    acc_bonus = (accuracy ** 5.5) * 5.5

    # Hidden/FL mod bonus
    from .beatmap import Mods
    mods = Mods(mods_int)
    mod_mult = 1.0
    if mods & Mods.HD:
        mod_mult *= 1.05 + 0.1 * min(1.0, (difficulty.n_fruits / 1000.0))
    if mods & Mods.FL:
        mod_mult *= 1.35 * (0.3 + 0.7 * (1.0 - 0.1 * difficulty.n_fruits / 200.0))

    pp = base * length_bonus * miss_penalty * combo_penalty * ar_bonus * acc_bonus * mod_mult

    if not passed and object_index is not None:
        # Partial score penalty
        ratio = object_index / max(1, difficulty.n_fruits + difficulty.n_droplets + difficulty.n_tiny_droplets)
        pp *= ratio ** 0.6

    return CatchPerformanceAttributes(
        pp=max(0.0, round(pp, 3)),
        difficulty=difficulty,
        accuracy=accuracy * 100.0,
        combo_ratio=combo_ratio,
    )


# Replay-informed projection
def project_catch_score(
    bm: CoreBeatmap,
    statistics: ScoreStatistics,
    combo: int,
    *,
    mods_int: int = 0,
    passed: bool = False,
    object_index: int | None = None,
) -> dict:
    """
    Full local catch analysis: difficulty + PP + if-FC projection.
    """
    diff = calculate_catch_difficulty(bm, mods_int)
    current = calculate_catch_performance(diff, statistics, combo, mods_int, passed, object_index)

    # FC projection: assume all remaining objects caught at same accuracy
    fc_stats = ScoreStatistics(
        count_300=diff.n_fruits + diff.n_droplets + diff.n_tiny_droplets,
    )
    fc = calculate_catch_performance(diff, fc_stats, diff.max_combo, mods_int, True)

    return {
        'stars': diff.stars,
        'ar': diff.ar,
        'max_combo': diff.max_combo,
        'n_fruits': diff.n_fruits,
        'n_droplets': diff.n_droplets,
        'n_tiny_droplets': diff.n_tiny_droplets,
        'hyper_dash_count': diff.hyper_dash_count,
        'current_pp': current.pp,
        'if_fc_pp': fc.pp,
        'accuracy': current.accuracy,
        'combo_ratio': current.combo_ratio,
        'mode': 'catch',
        'engine': 'local',
    }
