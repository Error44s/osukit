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
from typing import List, Optional

from .beatmap import Beatmap, HitCircle, Slider, Spinner, Vec2, Mods

# Constants  (matching osu!lazer / osukit-pp)
NORMALIZED_RADIUS = 50.0 # osu! normalised circle radius
MAXIMUM_SLIDER_RADIUS = NORMALIZED_RADIUS * 2.4
ASSUMED_SLIDER_RADIUS = NORMALIZED_RADIUS * 1.8

# Aim  (osukit-pp: Aim::SKILL_MULTIPLIER = 26.0)
AIM_SKILL_MULTIPLIER = 26.0
AIM_STRAIN_DECAY_BASE = 0.15

# Speed  (osukit-pp: Speed::SKILL_MULTIPLIER = 1.47)
SPEED_SKILL_MULTIPLIER = 1.47
SPEED_STRAIN_DECAY_BASE = 0.3
SINGLE_SPACING_THRESHOLD = 125.0
MIN_SPEED_BONUS = 75.0   # ms  (≈ 200 BPM 1/4)

# Flashlight  (osukit-pp: Flashlight::SKILL_MULTIPLIER = 0.05512)
FL_SKILL_MULTIPLIER  = 0.05512
FL_STRAIN_DECAY_BASE = 0.15

# OsuStrainSkill decay weight (osukit-pp StrainSkill::DECAY_WEIGHT = 0.9)
DECAY_WEIGHT = 0.9

# OsuStrainSkill reduced-section constants (osukit-pp)
REDUCED_SECTION_COUNT    = 10
REDUCED_STRAIN_BASELINE  = 0.75
SPEED_REDUCED_SECTION_COUNT = 5  # Speed overrides to 5
SECTION_LENGTH = 400.0

# Star rating (osukit-pp: STAR_RATING_MULTIPLIER = 0.0265, PERFORMANCE_BASE_MULTIPLIER = 1.14)
STAR_RATING_MULTIPLIER       = 0.0265
PERFORMANCE_BASE_MULTIPLIER  = 1.14

# Difficulty hit-object
@dataclass
class DiffHitObject:
    base: object # HitCircle | Slider | Spinner
    pos: Vec2 # stacked + normalised position
    last_pos: Vec2
    last_last_pos: Vec2
    time: float # ms (after clock-rate)
    delta_time: float # ms since last object *start* (after clock-rate)
    strain_time: float # max(delta_time, 25) — used for velocity

    jump_dist: float   = 0.0
    travel_dist: float = 0.0 # slider lazy-travel distance (normalised)
    movement_dist: float = 0.0
    angle: Optional[float] = None
    rhythm_complexity: float = 0.0
    # The great-window for this object (needed by speed evaluator)
    great_window: float = 35.0


def _get_stacked_pos(obj) -> Vec2:
    return getattr(obj, "_stacked_pos", obj.pos)

# lazy_travel_dist calculation (was always 0 before)
def _compute_lazy_travel_dist(slider: Slider, scale_factor: float) -> float:
    """
    Approximate the distance a cursor has to travel while following a slider.
    osu!lazer walks the path in discrete steps; we use a simpler but decent
    heuristic: sample several evenly-spaced points along the curve and sum up
    the movements, then clamp to MAXIMUM_SLIDER_RADIUS per span.

    For linear sliders this is exact.  For bezier/catmull/perfect-circle it is
    an approximation that is close enough for difficulty purposes.
    """
    points = slider.curve_points
    if not points or slider.pixel_length <= 0:
        # Fall back to pixel_length ÷ repeats as the minimum travel
        return min(slider.pixel_length * scale_factor, MAXIMUM_SLIDER_RADIUS)

    # Build a crude polygonal approximation of the curve
    # (we reuse the parsed curve_points which are the raw control points)
    def _walk_distance(pts: List[Vec2]) -> float:
        dist = 0.0
        for i in range(1, len(pts)):
            dx = pts[i].x - pts[i - 1].x
            dy = pts[i].y - pts[i - 1].y
            dist += math.hypot(dx, dy)
        return dist

    path_px = _walk_distance(points)
    # Clamp to pixel_length (the declared length in the .osu file)
    path_px = min(path_px, slider.pixel_length)

    # Scale to normalised space and account for repeats
    travel = path_px * scale_factor * slider.repeats
    return min(travel, MAXIMUM_SLIDER_RADIUS * slider.repeats)

# Build diff objects
def _build_diff_objects(
    hit_objects: list,
    clock_rate: float,
    cs: float,
    od: float,
) -> List[DiffHitObject]:
    """Convert raw hit objects into difficulty objects with precomputed geometry."""
    if not hit_objects:
        return []

    # osu! scale factor: maps playfield pixels → normalised coordinates
    scale_factor = NORMALIZED_RADIUS / (54.4 - 4.48 * cs)

    # Great-hit window for speed (ms, before clock-rate scaling – already
    # divided by clock_rate in the caller via strain_time)
    great_window_raw = (80.0 - 6.0 * od)  # ms at clock_rate 1×

    diff_objects: List[DiffHitObject] = []

    def norm(pos: Vec2) -> Vec2:
        return Vec2(pos.x * scale_factor, pos.y * scale_factor)

    last_pos       = norm(_get_stacked_pos(hit_objects[0]))
    last_last_pos  = last_pos

    for i, obj in enumerate(hit_objects):
        pos  = norm(_get_stacked_pos(obj))
        time = obj.time / clock_rate

        if i == 0:
            diff_objects.append(DiffHitObject(
                base=obj,
                pos=pos,
                last_pos=last_pos,
                last_last_pos=last_last_pos,
                time=time,
                delta_time=0,
                strain_time=50,
                great_window=great_window_raw / clock_rate,
            ))
            last_last_pos = last_pos
            last_pos      = pos
            continue

        prev = hit_objects[i - 1]
        delta_time  = (obj.time - prev.time) / clock_rate
        strain_time = max(delta_time, 25.0)

        dobj = DiffHitObject(
            base=obj,
            pos=pos,
            last_pos=last_pos,
            last_last_pos=last_last_pos,
            time=time,
            delta_time=delta_time,
            strain_time=strain_time,
            great_window=great_window_raw / clock_rate,
        )

        # jump distance
        if isinstance(prev, Slider):
            prev_end = getattr(prev, "_lazy_end_norm", None)
            if prev_end is None:
                # compute and cache
                if prev.curve_points:
                    if prev.repeats % 2 == 1:
                        # odd repeat count / single-span sliders end at the tail
                        tail_raw = prev.curve_points[-1]
                    else:
                        # even repeat count ends back at the head
                        tail_raw = _get_stacked_pos(prev)
                else:
                    tail_raw = _get_stacked_pos(prev)
                prev_end = norm(tail_raw)
                prev._lazy_end_norm = prev_end  # type: ignore[attr-defined]
            dobj.jump_dist = prev_end.distance_to(pos)
            dobj.travel_dist = _compute_lazy_travel_dist(prev, scale_factor)
            dobj.travel_dist = min(dobj.travel_dist, MAXIMUM_SLIDER_RADIUS)
        else:
            dobj.jump_dist   = last_pos.distance_to(pos)
            dobj.travel_dist = 0.0

        dobj.movement_dist = dobj.travel_dist + dobj.jump_dist

        # angle between previous → current → next vectors
        if i >= 2:
            v1 = Vec2(last_last_pos.x - last_pos.x, last_last_pos.y - last_pos.y)
            v2 = Vec2(pos.x - last_pos.x,           pos.y - last_pos.y)
            l1 = v1.length()
            l2 = v2.length()
            if l1 > 0 and l2 > 0:
                dot = max(-1.0, min(1.0, v1.dot(v2) / (l1 * l2)))
                dobj.angle = math.acos(dot)

        diff_objects.append(dobj)
        last_last_pos = last_pos
        last_pos      = pos

    return diff_objects

# Skill evaluators
def _evaluate_aim(curr: DiffHitObject, prev: DiffHitObject, with_sliders: bool) -> float:
    if isinstance(curr.base, Spinner):
        return 0.0

    curr_vel = curr.jump_dist / curr.strain_time
    if with_sliders and isinstance(prev.base, Slider):
        prev_vel = prev.travel_dist / prev.strain_time
        curr_vel = max(curr_vel, prev_vel)

    if curr.jump_dist == 0 and curr.travel_dist == 0:
        return 0.0

    wide_angle_bonus  = 0.0
    acute_angle_bonus = 0.0

    if curr.angle is not None and curr.angle > math.pi / 6:
        wide_angle_bonus = _calc_wide_angle_bonus(curr.angle)

    if curr.angle is not None and curr.angle < math.pi / 2:
        acute_angle_bonus = _calc_acute_angle_bonus(curr.angle)
        if curr.strain_time > 100:
            acute_angle_bonus = 0.0
        else:
            acute_angle_bonus *= _smooth_step(0, 1, (100 - curr.strain_time) / 25)

    aim_strain = curr_vel

    if wide_angle_bonus > 0:
        aim_strain += wide_angle_bonus * curr_vel
    if acute_angle_bonus > 0:
        aim_strain += acute_angle_bonus * max(0, curr_vel - 0.5)

    if with_sliders and isinstance(curr.base, Slider):
        aim_strain += curr.travel_dist / curr.strain_time

    return aim_strain




def _compute_section_peaks(
    diff_objects: List[DiffHitObject],
    decay_base: float,
    value_fn,
    skill_multiplier: float,
):
    """Compute osu!-style 400ms section peaks for a strain skill."""
    if not diff_objects:
        return [], []

    if len(diff_objects) == 1:
        return [0.0], [0.0]

    section_end = math.ceil(diff_objects[0].time / SECTION_LENGTH) * SECTION_LENGTH
    current_strain = 0.0
    current_section_peak = 0.0
    object_strains: List[float] = [0.0]
    section_peaks: List[float] = []

    for i in range(1, len(diff_objects)):
        curr = diff_objects[i]
        prev = diff_objects[i - 1]

        while curr.time > section_end:
            section_peaks.append(current_section_peak)
            current_strain *= math.pow(decay_base, (section_end - prev.time) / 1000.0)
            current_section_peak = current_strain
            section_end += SECTION_LENGTH

        strain_value = value_fn(curr, prev)
        current_strain *= math.pow(decay_base, curr.delta_time / 1000.0)
        current_strain += strain_value * skill_multiplier

        object_strains.append(current_strain)
        current_section_peak = max(current_section_peak, current_strain)

    section_peaks.append(current_section_peak)

    return object_strains, section_peaks

def _calc_wide_angle_bonus(angle: float) -> float:
    return math.pow(math.sin(3.0 / 4.0 * (min(5.0 / 6.0 * math.pi, angle) - math.pi / 6)), 2)


def _calc_acute_angle_bonus(angle: float) -> float:
    return math.pow(math.sin(1.5 * (max(0, angle - math.pi / 6))), 2)


def _smooth_step(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _evaluate_speed(curr: DiffHitObject) -> float:
    if isinstance(curr.base, Spinner):
        return 0.0

    strain_time  = curr.strain_time
    great_window = curr.great_window

    # Cap strain_time to hit window (osukit-pp: strain_time /= clamp(strain_time/hw/0.93, 0.92, 1.0))
    if great_window > 0:
        ratio = strain_time / great_window / 0.93
        strain_time /= max(0.92, min(1.0, ratio))

    dist = min(SINGLE_SPACING_THRESHOLD, curr.travel_dist + curr.jump_dist)

    # Speed bonus for BPM > 200 (MIN_SPEED_BONUS = 75ms)
    speed_bonus = 0.0
    if strain_time < MIN_SPEED_BONUS:
        speed_bonus = 0.75 * math.pow((MIN_SPEED_BONUS - strain_time) / 40.0, 2)

    # Distance bonus: osukit-pp uses (dist/threshold)^3.95 * 0.8
    dist_bonus = math.pow(dist / SINGLE_SPACING_THRESHOLD, 3.95) * 0.8

    # Base difficulty (osukit-pp: (1 + speed_bonus + dist_bonus) * 1000 / strain_time)
    return (1.0 + speed_bonus + dist_bonus) * 1000.0 / strain_time


def _evaluate_flashlight(curr: DiffHitObject, hidden: bool) -> float:
    if isinstance(curr.base, Spinner):
        return 0.0

    scaling_factor = 52.0
    opacity_bonus  = 1.0
    if hidden:
        opacity_bonus = 1.0 + 0.4 * min(1.0, curr.jump_dist / scaling_factor)

    result = math.pow(0.8, max(0, curr.jump_dist / scaling_factor - 1)) * opacity_bonus
    return result

# Strain → difficulty value
def _difficulty_value(
    strains: List[float],
    decay_weight: float = DECAY_WEIGHT,
    reduced_section_count: int = REDUCED_SECTION_COUNT,
    reduced_strain_baseline: float = REDUCED_STRAIN_BASELINE,
) -> float:
    """Weighted sum of sorted strains — matches osukit-pp OsuStrainSkill::difficulty_value.

    The top `reduced_section_count` strains are scaled down logarithmically
    (the "reduced section" mechanic) before the weighted sum is computed.
    Strains of 0 are excluded (osukit-pp excludes zero-strain sections).
    """
    if not strains:
        return 0.0

    # Exclude zero-strain sections (osukit-pp does this to avoid worst-case sort)
    peaks = [s for s in strains if s > 0.0]
    if not peaks:
        return 0.0

    sorted_strains = sorted(peaks, reverse=True)

    # Apply reduced-section scaling to the top strains
    for i in range(min(reduced_section_count, len(sorted_strains))):
        clamped = i / reduced_section_count  # already in [0,1]
        import math as _math
        scale = _math.log10(1.0 + 9.0 * clamped)  # lerp(1,10,clamped) then log10
        sorted_strains[i] *= reduced_strain_baseline + (1.0 - reduced_strain_baseline) * scale

    # Re-sort after scaling (top strains were reduced, order may shift)
    sorted_strains.sort(reverse=True)

    difficulty = 0.0
    weight     = 1.0
    for s in sorted_strains:
        difficulty += s * weight
        weight     *= decay_weight
    return difficulty

# Star rating helpers
def _difficulty_to_performance(difficulty: float) -> float:
    """Convert a difficulty rating (aim_stars / speed_stars) to raw performance value.
    Matches osukit-pp: difficulty_to_performance(d) = (5*max(1, d/0.0675) - 4)^3 / 100_000
    """
    return math.pow(5.0 * max(1.0, difficulty / 0.0675) - 4.0, 3.0) / 100_000.0


def _flashlight_difficulty_to_performance(difficulty: float) -> float:
    """Matches osukit-pp Flashlight::difficulty_to_performance = 25 * d^2"""
    return 25.0 * math.pow(difficulty, 2.0)


def _scale_difficulty(difficulty: float) -> float:
    """Convert raw weighted-strain sum to star-rating component (same as osukit-pp).
    difficulty_rating = sqrt(difficulty_value) * DIFFICULTY_MULTIPLIER (0.0675)
    """
    if difficulty <= 0:
        return 0.0
    return math.sqrt(difficulty) * 0.0675


def _star_rating(aim: float, speed: float, fl: float) -> float:
    """Combine skill star values into overall star rating — matches osukit-pp exactly.

    osukit-pp approach:
      1. Convert each skill rating to a base-performance value
      2. Combine via powf(1.1) norm
      3. Convert combined performance back to stars via:
         stars = cbrt(PERFORMANCE_BASE_MULTIPLIER) * STAR_RATING_MULTIPLIER
                 * (cbrt(100_000 / 2^(1/1.1) * base_performance) + 4)
    """
    base_aim   = _difficulty_to_performance(aim)
    base_speed = _difficulty_to_performance(speed)
    base_fl    = _flashlight_difficulty_to_performance(fl) if fl > 0 else 0.0

    base_perf = math.pow(
        math.pow(base_aim,   1.1)
        + math.pow(base_speed, 1.1)
        + math.pow(base_fl,   1.1),
        1.0 / 1.1,
    )

    if base_perf <= 1e-5:
        return 0.0

    return (
        math.pow(PERFORMANCE_BASE_MULTIPLIER, 1.0 / 3.0)
        * STAR_RATING_MULTIPLIER
        * (math.pow(100_000.0 / math.pow(2.0, 1.0 / 1.1) * base_perf, 1.0 / 3.0) + 4.0)
    )

# DifficultyAttributes result
@dataclass
class DifficultyAttributes:
    stars:                         float = 0.0
    aim_difficulty:                float = 0.0
    speed_difficulty:              float = 0.0
    flashlight_difficulty:         float = 0.0
    slider_factor:                 float = 1.0
    speed_note_count:              float = 0.0
    aim_difficult_strain_count:    float = 0.0
    speed_difficult_strain_count:  float = 0.0
    approach_rate:                 float = 0.0
    overall_difficulty:            float = 0.0
    drain_rate:                    float = 0.0
    hit_circle_count:              int   = 0
    slider_count:                  int   = 0
    spinner_count:                 int   = 0
    max_combo:                     int   = 0

# Public API
def calculate_difficulty(
    beatmap: Beatmap,
    mods: Mods = Mods.NM,
    clock_rate: Optional[float] = None,
    ar_override: Optional[float] = None,
    od_override: Optional[float] = None,
    cs_override: Optional[float] = None,
) -> DifficultyAttributes:
    """
    Calculate difficulty attributes for osu! standard.

    Parameters
    ----------
    beatmap     : parsed Beatmap object
    mods        : Mods bitfield (default NM)
    clock_rate  : override clock rate (default derived from mods)
    ar_override : override approach rate (after mod scaling)
    od_override : override overall difficulty (after mod scaling)
    cs_override : override circle size (after mod scaling)
    """
    cr = clock_rate if clock_rate is not None else mods.speed_multiplier

    cs = min(10.0, (cs_override if cs_override is not None else beatmap.cs) * mods.cs_multiplier)
    ar_raw = (ar_override if ar_override is not None else beatmap.ar)
    od_raw = (od_override if od_override is not None else beatmap.od)
    ar = min(10.0, ar_raw * mods.ar_multiplier)
    od = min(10.0, od_raw * mods.od_multiplier)

    hit_objects = beatmap.hit_objects
    if not hit_objects:
        return DifficultyAttributes()

    diff_objects = _build_diff_objects(hit_objects, cr, cs, od)

    # Aim strain (object strains + 400ms section peaks)
    aim_object_strains, aim_section_peaks = _compute_section_peaks(
        diff_objects,
        AIM_STRAIN_DECAY_BASE,
        lambda curr, prev: _evaluate_aim(curr, prev, True),
        AIM_SKILL_MULTIPLIER,
    )
    aim_no_slider_object_strains, aim_no_slider_section_peaks = _compute_section_peaks(
        diff_objects,
        AIM_STRAIN_DECAY_BASE,
        lambda curr, prev: _evaluate_aim(curr, prev, False),
        AIM_SKILL_MULTIPLIER,
    )

    aim_diff = _difficulty_value(aim_section_peaks)
    aim_diff_no_sliders = _difficulty_value(aim_no_slider_section_peaks)
    slider_factor = aim_diff_no_sliders / aim_diff if aim_diff > 0 else 1.0

    # Speed strain (use section peaks for star difficulty, object strains for note count)
    speed_object_strains, speed_section_peaks = _compute_section_peaks(
        diff_objects,
        SPEED_STRAIN_DECAY_BASE,
        lambda curr, prev: _evaluate_speed(curr),
        SPEED_SKILL_MULTIPLIER,
    )

    speed_diff = _difficulty_value(
        speed_section_peaks,
        reduced_section_count=SPEED_REDUCED_SECTION_COUNT,
    )

    # Speed note count (logistic weighting)
    speed_note_count  = 0.0
    object_strains    = sorted([s for s in speed_object_strains if s > 0], reverse=True)
    if object_strains:
        max_strain = object_strains[0]
        if max_strain > 0:
            speed_note_count = sum(
                1.0 / (1.0 + math.exp(-(s / max_strain * 12.0 - 6.0)))
                for s in object_strains
            )

    # Aim difficult strain count
    aim_note_count     = 0.0
    aim_sorted         = sorted(aim_object_strains, reverse=True)
    if aim_sorted and aim_sorted[0] > 0:
        max_aim = aim_sorted[0]
        aim_note_count = sum(
            1.0 / (1.0 + math.exp(-(s / max_aim * 12.0 - 6.0)))
            for s in aim_sorted
        )

    # Flashlight strain
    fl_diff     = 0.0
    with_hidden = bool(mods & Mods.HD)
    if mods & Mods.FL:
        current_fl = 0.0
        fl_strains: List[float] = []
        for i, curr in enumerate(diff_objects):
            if i == 0:
                fl_strains.append(0.0)
                continue
            decay      = math.pow(FL_STRAIN_DECAY_BASE, curr.delta_time / 1000.0)
            current_fl = current_fl * decay + _evaluate_flashlight(curr, with_hidden) * FL_SKILL_MULTIPLIER
            fl_strains.append(current_fl)
        fl_diff = _difficulty_value(fl_strains)

    # Combine
    aim_stars   = _scale_difficulty(aim_diff)
    speed_stars = _scale_difficulty(speed_diff)
    fl_stars    = _scale_difficulty(fl_diff)
    stars       = _star_rating(aim_stars, speed_stars, fl_stars)

    # Effective AR (after clock-rate)
    if ar < 5:
        ar_ms = 1800.0 - 120.0 * ar
    else:
        ar_ms = 1200.0 - 150.0 * (ar - 5.0)
    ar_ms /= cr
    if ar_ms > 1200.0:
        ar_eff = (1800.0 - ar_ms) / 120.0
    else:
        ar_eff = (1200.0 - ar_ms) / 150.0 + 5.0
    ar_eff = max(0.0, min(11.0, ar_eff))

    # Effective OD (after clock-rate)
    hit_window_300 = 80.0 - 6.0 * od
    hit_window_300 /= cr
    od_eff = (80.0 - hit_window_300) / 6.0
    od_eff = max(0.0, min(11.0, od_eff))

    return DifficultyAttributes(
        stars=max(0.0, stars),
        aim_difficulty=max(0.0, aim_stars),
        speed_difficulty=max(0.0, speed_stars),
        flashlight_difficulty=max(0.0, fl_stars),
        slider_factor=slider_factor,
        speed_note_count=speed_note_count,
        aim_difficult_strain_count=aim_note_count,
        speed_difficult_strain_count=speed_note_count,
        approach_rate=ar_eff,
        overall_difficulty=od_eff,
        drain_rate=beatmap.hp,
        hit_circle_count=beatmap.n_circles,
        slider_count=beatmap.n_sliders,
        spinner_count=beatmap.n_spinners,
        max_combo=beatmap.max_combo,
    )
