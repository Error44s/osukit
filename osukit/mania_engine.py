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
from typing import Sequence

from .beatmap import Beatmap as CoreBeatmap, Slider, Spinner, HitCircle
from .models import ScoreStatistics

# Difficulty Attributes
@dataclass
class ManiaDifficultyAttributes:
    stars: float
    hit_window: float # OD-based 300 window in ms
    n_notes: int
    n_hold_notes: int
    key_count: int
    max_combo: int
    strain_peaks: list[float] = field(default_factory=list)

    @property
    def total_objects(self) -> int:
        return self.n_notes + self.n_hold_notes


@dataclass
class ManiaPerformanceAttributes:
    pp: float
    difficulty: ManiaDifficultyAttributes
    accuracy: float
    score_pp: float
    acc_pp: float

# Helpers
def _mania_hit_window_300(od: float, mods_int: int = 0) -> float:
    from .beatmap import Mods
    mods = Mods(mods_int)
    od_adj = max(0.0, min(10.0, od * mods.od_multiplier))
    return max(34.0, 34.0 + 3.0 * (10.0 - od_adj))  # ~64ms at OD0, ~34ms at OD10


def _key_count_from_cs(cs: float) -> int:
    return max(1, min(10, round(cs)))


def _column_of_object(obj, key_count: int) -> int:
    x = getattr(getattr(obj, 'pos', None), 'x', 0.0)
    return min(key_count - 1, int(x * key_count / 512.0))


# Difficulty calculation
def calculate_mania_difficulty(bm: CoreBeatmap, mods_int: int = 0) -> ManiaDifficultyAttributes:
    """
    Local mania difficulty approximation.

    Key factors:
    - Note density (notes per second)
    - Hold note complexity
    - Column balance (spread of notes across keys)
    - OD-based hit window
    """
    from .beatmap import Mods
    mods = Mods(mods_int)
    key_count = _key_count_from_cs(bm.cs)
    od = max(0.0, min(10.0, bm.od * mods.od_multiplier))
    hit_window = _mania_hit_window_300(bm.od, mods_int)

    n_notes = sum(1 for o in bm.hit_objects if isinstance(o, HitCircle))
    n_holds = sum(1 for o in bm.hit_objects if isinstance(o, Slider))
    max_combo = n_notes + n_holds * 2  # head + tail of each hold

    if not bm.hit_objects:
        return ManiaDifficultyAttributes(
            stars=0.0, hit_window=hit_window, n_notes=n_notes,
            n_hold_notes=n_holds, key_count=key_count, max_combo=max_combo,
        )

    total_objs = len(bm.hit_objects)
    first_time = float(getattr(bm.hit_objects[0], 'time', 0))
    last_time = float(getattr(bm.hit_objects[-1], 'end_time', getattr(bm.hit_objects[-1], 'time', 0)))
    duration_s = max(1.0, (last_time - first_time) / 1000.0)

    note_density = total_objs / duration_s

    # Column distribution (imbalance increases difficulty)
    col_counts = [0] * key_count
    for obj in bm.hit_objects:
        col = _column_of_object(obj, key_count)
        col_counts[col] += 1
    avg_col = total_objs / max(key_count, 1)
    col_variance = sum((c - avg_col) ** 2 for c in col_counts) / max(key_count, 1)
    col_imbalance = math.sqrt(col_variance) / max(avg_col, 1)

    # Hold note density
    hold_ratio = n_holds / max(total_objs, 1)

    # Speed factor
    speed = mods.speed_multiplier

    # Base star calculation
    od_factor = 1.0 + (od - 5.0) * 0.04
    base = (
        0.4 * note_density
        + 0.15 * col_imbalance
        + 0.25 * hold_ratio * note_density
    ) * od_factor * speed

    # Key count scaling: 4K is harder than 7K in terms of density per column
    key_factor = (7.0 / max(key_count, 1)) ** 0.5
    stars = round(max(0.0, base * key_factor), 4)

    # Compute rough strain peaks per second for visualization
    window_ms = 500.0
    strain_peaks: list[float] = []
    times = [float(getattr(o, 'time', 0)) for o in bm.hit_objects]
    t = first_time
    while t < last_time:
        count = sum(1 for ot in times if t <= ot < t + window_ms)
        strain_peaks.append(count / (window_ms / 1000.0))
        t += window_ms

    return ManiaDifficultyAttributes(
        stars=stars,
        hit_window=hit_window,
        n_notes=n_notes,
        n_hold_notes=n_holds,
        key_count=key_count,
        max_combo=max_combo,
        strain_peaks=strain_peaks,
    )

# Performance calculation
def calculate_mania_performance(
    difficulty: ManiaDifficultyAttributes,
    statistics: ScoreStatistics,
    mods_int: int = 0,
    score: int = 0,
    passed: bool = True,
    object_index: int | None = None,
) -> ManiaPerformanceAttributes:
    """
    Local mania PP approximation.

    osu!mania PP uses two components:
      1. Score-based PP (from legacy score value)
      2. Accuracy-based PP (from hit accuracy)
    """
    from .beatmap import Mods
    mods = Mods(mods_int)
    stars = difficulty.stars

    if stars <= 0 or difficulty.max_combo <= 0:
        return ManiaPerformanceAttributes(
            pp=0.0, difficulty=difficulty, accuracy=0.0, score_pp=0.0, acc_pp=0.0
        )

    total = (statistics.count_300 + statistics.count_100 + statistics.count_50
             + statistics.count_miss + statistics.katu + statistics.geki)
    if total <= 0:
        accuracy = 100.0
    else:
        accuracy = (
            (320 * statistics.geki + 300 * statistics.count_300
             + 200 * statistics.katu + 100 * statistics.count_100
             + 50 * statistics.count_50)
            / (305.0 * total)
        ) * 100.0
    accuracy = max(0.0, min(100.0, accuracy))

    # Score-based component
    # Normalise score to 0-1 range (max score = 1,000,000)
    score_ratio = min(1.0, score / 1_000_000) if score > 0 else (accuracy / 100.0)

    # Base difficulty value
    diff_value = ((5.0 * stars / 0.2) - 4.0) ** 2.2 / 135.0
    diff_value *= 1.0 + 0.1 * min(1.0, difficulty.total_objects / 1500.0)

    # Score pp: strong scaling with score
    if score_ratio < 0.5:
        score_pp = diff_value * ((score_ratio * 2) ** 10.0) * 0.1
    else:
        score_pp = diff_value * (1.0 - 0.22 * (1.0 - score_ratio) ** 1.1)

    # Accuracy pp
    hit_window = difficulty.hit_window
    acc_value = max(0.0, 1.5 * (0.26 - hit_window / 1000.0)) * 2.83
    acc_value *= min(1.15, (accuracy / 95.0) ** 11.0)
    acc_pp = acc_value

    # Mod adjustments
    mod_mult = 1.0
    if mods & Mods.NF:
        mod_mult *= 0.75
    if mods & Mods.EZ:
        mod_mult *= 0.5
    if mods & Mods.HT:
        mod_mult *= 0.5

    # Combine: weighted sum
    pp = (score_pp ** 1.1 + acc_pp ** 1.1) ** (1.0 / 1.1) * mod_mult

    if not passed and object_index is not None:
        ratio = object_index / max(1, difficulty.total_objects)
        pp *= ratio ** 0.5

    return ManiaPerformanceAttributes(
        pp=max(0.0, round(pp, 3)),
        difficulty=difficulty,
        accuracy=accuracy,
        score_pp=score_pp,
        acc_pp=acc_pp,
    )

# Replay-informed projection
def project_mania_score(
    bm: CoreBeatmap,
    statistics: ScoreStatistics,
    *,
    mods_int: int = 0,
    score: int = 0,
    passed: bool = False,
    object_index: int | None = None,
) -> dict:
    """
    Full local mania analysis: difficulty + PP + projection.
    """
    diff = calculate_mania_difficulty(bm, mods_int)
    current = calculate_mania_performance(diff, statistics, mods_int, score, passed, object_index)

    # Perfect projection
    perfect_stats = ScoreStatistics(geki=diff.total_objects)
    fc = calculate_mania_performance(diff, perfect_stats, mods_int, 1_000_000, True)

    return {
        'stars': diff.stars,
        'hit_window_300': diff.hit_window,
        'key_count': diff.key_count,
        'max_combo': diff.max_combo,
        'n_notes': diff.n_notes,
        'n_hold_notes': diff.n_hold_notes,
        'current_pp': current.pp,
        'if_fc_pp': fc.pp,
        'accuracy': current.accuracy,
        'score_pp': current.score_pp,
        'acc_pp': current.acc_pp,
        'mode': 'mania',
        'engine': 'local',
    }
