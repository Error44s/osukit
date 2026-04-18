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
from typing import List, Optional, Tuple

from .beatmap import Beatmap, HitCircle, Slider, Spinner, TimingPoint, Mods

# Taiko note types
class TaikoNoteType:
    DON = 0   # red (centre hit)
    KAT = 1   # blue (rim hit)


@dataclass
class TaikoHitObject:
    """A single taiko hit (don or kat, small or large)."""
    time: float           # ms (clock-rate-adjusted)
    raw_time: float       # ms original
    note_type: int        # DON or KAT
    is_large: bool = False
    is_drum_roll: bool = False
    is_swell: bool = False
    delta_time: float = 0.0   # ms since previous note
    strain_time: float = 0.0  # clamped delta_time

# Convert osu! standard objects → Taiko hit objects
def _convert_to_taiko(beatmap: Beatmap, clock_rate: float) -> List[TaikoHitObject]:
    """
    Convert a parsed Beatmap (any mode) into a flat list of TaikoHitObjects.
    In osu! standard converts, each circle becomes a don/kat based on hitsound.
    Each slider becomes a drum roll, spinners become swells.
    Native taiko maps have explicit note types encoded in the hit objects.
    """
    objects: List[TaikoHitObject] = []

    for obj in beatmap.hit_objects:
        if isinstance(obj, HitCircle):
            # Alternate don/kat (simplified — real taiko uses hitsound sample sets)
            # We use position X as a proxy: x >= 256 → kat, else → don
            note_type = TaikoNoteType.KAT if obj.pos.x >= 256 else TaikoNoteType.DON
            objects.append(TaikoHitObject(
                time=obj.time / clock_rate,
                raw_time=obj.time,
                note_type=note_type,
                is_large=False,
            ))
        elif isinstance(obj, Slider):
            # Drum roll — add a hit at the head only for difficulty purposes
            objects.append(TaikoHitObject(
                time=obj.time / clock_rate,
                raw_time=obj.time,
                note_type=TaikoNoteType.DON,
                is_drum_roll=True,
            ))
        elif isinstance(obj, Spinner):
            objects.append(TaikoHitObject(
                time=obj.time / clock_rate,
                raw_time=obj.time,
                note_type=TaikoNoteType.DON,
                is_swell=True,
            ))

    # Sort and compute delta times
    objects.sort(key=lambda o: o.time)
    for i, obj in enumerate(objects):
        if i == 0:
            obj.delta_time = 0.0
        else:
            obj.delta_time = obj.time - objects[i - 1].time
        obj.strain_time = max(obj.delta_time, 25.0)

    return objects

# Skill: Stamina
STAMINA_SKILL_MULTIPLIER = 1.0
STAMINA_STRAIN_DECAY_BASE = 0.4


def _evaluate_stamina(curr: TaikoHitObject, note_history: List[TaikoHitObject]) -> float:
    """
    Stamina measures how hard it is to sustain hitting.
    Same-hand notes 2 apart (alternating pattern) create strain.
    """
    if curr.is_drum_roll or curr.is_swell:
        return 0.0

    # Find the previous same-hand note (2 positions back in history)
    if len(note_history) < 2:
        return 0.0

    prev_same = note_history[-2]  # same hand hit (2 notes ago)
    if prev_same.is_drum_roll or prev_same.is_swell:
        return 0.0

    strain_time = curr.time - prev_same.time
    strain_time = max(strain_time, 25.0)

    # Speed bonus: faster hits = more stamina strain
    speed = 1.0 / strain_time
    # Bonus for very fast 1/4 streams
    speed_bonus = 0.0
    if strain_time < 160.0:   # ~187.5 BPM 1/4
        speed_bonus = (160.0 - strain_time) / 160.0
        speed_bonus = speed_bonus * speed_bonus

    return (1.0 + speed_bonus) / strain_time * 175.0

# Skill: Colour
COLOUR_SKILL_MULTIPLIER = 0.375
COLOUR_STRAIN_DECAY_BASE = 0.4


def _evaluate_colour(curr: TaikoHitObject, prev: TaikoHitObject, history: List[TaikoHitObject]) -> float:
    """
    Colour (don/kat alternation) difficulty.
    Penalises monotone patterns; rewards switches and complex patterns.
    """
    if curr.is_drum_roll or curr.is_swell:
        return 0.0
    if prev.is_drum_roll or prev.is_swell:
        return 0.0

    # Colour switch bonus: reward switching between don and kat
    colour_change = curr.note_type != prev.note_type
    base = 0.5 if colour_change else 0.0

    # Pattern complexity (look back up to 4 notes)
    alternating_bonus = 0.0
    if len(history) >= 4:
        recent = history[-4:]
        types = [h.note_type for h in recent] + [curr.note_type]
        # Count transitions
        transitions = sum(1 for a, b in zip(types, types[1:]) if a != b)
        alternating_bonus = transitions / 4.0 * 0.5

    return (base + alternating_bonus) / curr.strain_time * 100.0

# Skill: Rhythm
RHYTHM_SKILL_MULTIPLIER = 1.0
RHYTHM_STRAIN_DECAY_BASE = 0.3


# Rhythm ratios that get a bonus (powers of 2 and some others)
_RHYTHM_RATIOS = {
    2.0: 0.3,
    0.5: 0.3,
    1.5: 0.6,
    0.667: 0.6,  # 2/3
    1.333: 0.6,  # 4/3
    0.75: 0.3,
    1.25: 0.2,
    0.8: 0.2,
}


def _evaluate_rhythm(curr: TaikoHitObject, prev: TaikoHitObject, prev_prev: Optional[TaikoHitObject]) -> float:
    """
    Rhythm difficulty: measures how complex the timing pattern is.
    Sudden BPM changes or unusual rhythms score higher.
    """
    if curr.is_drum_roll or curr.is_swell:
        return 0.0

    if prev_prev is None or prev.is_drum_roll or prev_prev.is_drum_roll:
        return 0.0

    curr_dt = curr.delta_time
    prev_dt = prev.delta_time

    if prev_dt <= 0 or curr_dt <= 0:
        return 0.0

    ratio = curr_dt / prev_dt

    # Find nearest "expected" ratio for bonus
    rhythm_bonus = 0.0
    for expected_ratio, bonus in _RHYTHM_RATIOS.items():
        if abs(ratio - expected_ratio) < 0.1:
            rhythm_bonus = bonus
            break

    # Also penalise if ratio is very close to 1.0 (monotone → low rhythm)
    if abs(ratio - 1.0) < 0.05:
        return 0.0

    # Island bonus: sequences of same-interval notes
    strain = (rhythm_bonus + 0.2) / curr.strain_time * 100.0
    return max(0.0, strain)

# Section-peak aggregation (same as osu!lazer)
SECTION_LENGTH_MS = 400.0


def _compute_section_peaks(
    objects: List[TaikoHitObject],
    evaluator,
    decay_base: float,
) -> Tuple[List[float], List[float]]:
    """Returns (strains_per_object, section_peaks)."""
    if not objects:
        return [], []

    strains: List[float] = [0.0]
    current_strain = 0.0
    section_peaks: List[float] = []
    section_max = 0.0
    current_section_end = (
        math.ceil(objects[0].time / SECTION_LENGTH_MS) * SECTION_LENGTH_MS
    )

    history: List[TaikoHitObject] = []

    for i in range(1, len(objects)):
        curr = objects[i]
        prev = objects[i - 1]
        prev_prev = objects[i - 2] if i >= 2 else None

        decay = math.pow(decay_base, curr.delta_time / 1000.0)
        current_strain *= decay
        current_strain += evaluator(curr, prev, prev_prev, history)
        strains.append(current_strain)
        history.append(prev)

        # Track section peak
        while curr.time > current_section_end:
            section_peaks.append(section_max)
            section_max = 0.0
            current_section_end += SECTION_LENGTH_MS

        section_max = max(section_max, current_strain)

    section_peaks.append(section_max)
    return strains, section_peaks


def _difficulty_value(section_peaks: List[float], decay_weight: float = 0.9) -> float:
    """Weighted sum of sorted section peaks → single difficulty value."""
    if not section_peaks:
        return 0.0
    sorted_peaks = sorted(section_peaks, reverse=True)
    difficulty = 0.0
    weight = 1.0
    for peak in sorted_peaks:
        difficulty += peak * weight
        weight *= decay_weight
    return difficulty

# Taiko Difficulty Attributes
@dataclass
class TaikoDifficultyAttributes:
    stars: float = 0.0
    stamina_difficulty: float = 0.0
    rhythm_difficulty: float = 0.0
    colour_difficulty: float = 0.0
    peak_difficulty: float = 0.0
    great_hit_window: float = 0.0
    overall_difficulty: float = 0.0
    max_combo: int = 0

# Public API: Taiko Difficulty Calculator
def calculate_taiko_difficulty(
    beatmap: Beatmap,
    mods: Mods = Mods.NM,
    clock_rate: Optional[float] = None,
    od_override: Optional[float] = None,
) -> TaikoDifficultyAttributes:
    """
    Calculate Taiko difficulty attributes.

    Parameters
    ----------
    beatmap     : parsed Beatmap object
    mods        : Mods bitfield
    clock_rate  : override clock rate
    od_override : override OD
    """
    cr = clock_rate if clock_rate is not None else mods.speed_multiplier
    od_raw = od_override if od_override is not None else beatmap.od
    od = min(10.0, od_raw * mods.od_multiplier)

    objects = _convert_to_taiko(beatmap, cr)
    # Only care about hits (not drum rolls, swells) for difficulty
    hit_objects = [o for o in objects if not o.is_drum_roll and not o.is_swell]

    if len(hit_objects) < 2:
        return TaikoDifficultyAttributes()

    # Stamina (two-handed: left and right tracks separately)
    # We alternate: even-index = right hand, odd-index = left hand
    right_hand = hit_objects[0::2]
    left_hand  = hit_objects[1::2]

    def stamina_eval(curr, prev, prev_prev, history):
        return _evaluate_stamina(curr, history)

    _, right_peaks = _compute_section_peaks(right_hand, stamina_eval, STAMINA_STRAIN_DECAY_BASE)
    _, left_peaks  = _compute_section_peaks(left_hand,  stamina_eval, STAMINA_STRAIN_DECAY_BASE)

    stamina_rating = (
        _difficulty_value(right_peaks) + _difficulty_value(left_peaks)
    ) * STAMINA_SKILL_MULTIPLIER * 0.00016

    # Colour
    def colour_eval(curr, prev, prev_prev, history):
        return _evaluate_colour(curr, prev, history)

    _, colour_peaks = _compute_section_peaks(hit_objects, colour_eval, COLOUR_STRAIN_DECAY_BASE)
    colour_rating = _difficulty_value(colour_peaks) * COLOUR_SKILL_MULTIPLIER * 0.000064

    # Rhythm
    def rhythm_eval(curr, prev, prev_prev, history):
        return _evaluate_rhythm(curr, prev, prev_prev)

    _, rhythm_peaks = _compute_section_peaks(hit_objects, rhythm_eval, RHYTHM_STRAIN_DECAY_BASE)
    rhythm_rating = _difficulty_value(rhythm_peaks) * RHYTHM_SKILL_MULTIPLIER * 0.000075

    # Colour-stamina penalty
    stamina_penalty = _simple_colour_penalty(stamina_rating, colour_rating)

    # Separated rating (L-p norm, p=1.5)
    def norm(p: float, *values: float) -> float:
        return math.pow(sum(math.pow(abs(v), p) for v in values), 1.0 / p)

    separated_rating = norm(1.5, colour_rating, rhythm_rating, stamina_rating)

    # Combined (peak-based) rating
    combined_rating = _locally_combined_difficulty(
        colour_peaks, rhythm_peaks, right_peaks, left_peaks, stamina_penalty
    )

    # Final star rating
    star_rating = 1.4 * separated_rating + 0.5 * combined_rating

    # Rescale to keep live scores below ~9.5 stars
    star_rating = _rescale(star_rating)

    # Great hit window (ms)
    great_hit_window = (80.0 - 6.0 * od) / cr

    # Peak difficulty (just combined for attribute output)
    peak_difficulty = combined_rating

    return TaikoDifficultyAttributes(
        stars=max(0.0, star_rating),
        stamina_difficulty=stamina_rating,
        rhythm_difficulty=rhythm_rating,
        colour_difficulty=colour_rating,
        peak_difficulty=peak_difficulty,
        great_hit_window=great_hit_window,
        overall_difficulty=od,
        max_combo=len(hit_objects),
    )


def _simple_colour_penalty(stamina: float, colour: float) -> float:
    """Reduce stamina rating for very colourless maps."""
    if colour <= 0:
        return 0.79 - 0.25
    return 0.79 - math.atan(stamina / colour - 12.0) / math.pi / 2.0


def _locally_combined_difficulty(
    colour_peaks: List[float],
    rhythm_peaks: List[float],
    right_peaks: List[float],
    left_peaks: List[float],
    stamina_penalty: float,
) -> float:
    """Combine per-section peaks of all skills."""
    # Pad shorter lists to same length
    n = max(len(colour_peaks), len(rhythm_peaks), len(right_peaks), len(left_peaks))

    def pad(lst: List[float]) -> List[float]:
        return lst + [0.0] * (n - len(lst))

    cp = pad(colour_peaks)
    rp = pad(rhythm_peaks)
    sp_r = pad(right_peaks)
    sp_l = pad(left_peaks)

    peaks = []
    for i in range(n):
        col  = cp[i]  * COLOUR_SKILL_MULTIPLIER * 0.000064
        rhy  = rp[i]  * RHYTHM_SKILL_MULTIPLIER * 0.000075
        sta  = (sp_r[i] + sp_l[i]) * STAMINA_SKILL_MULTIPLIER * 0.00016 * stamina_penalty
        combined = math.sqrt(col ** 2 + rhy ** 2 + sta ** 2)  # L-2 norm
        peaks.append(combined)

    sorted_peaks = sorted(peaks, reverse=True)
    difficulty = 0.0
    weight = 1.0
    for p in sorted_peaks:
        difficulty += p * weight
        weight *= 0.9

    return difficulty


def _rescale(stars: float) -> float:
    """Rescaling to keep the curve consistent with historical data."""
    if stars < 0:
        return stars
    # Soft clamp: gradually reduce growth above ~8 stars
    if stars > 8.0:
        excess = stars - 8.0
        stars = 8.0 + math.sqrt(excess) * 0.5
    return stars
