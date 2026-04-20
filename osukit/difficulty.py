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

NORMALIZED_RADIUS = 50.0
MAXIMUM_SLIDER_RADIUS = NORMALIZED_RADIUS * 2.4
ASSUMED_SLIDER_RADIUS = NORMALIZED_RADIUS * 1.8

AIM_SKILL_MULTIPLIER = 23.55
AIM_STRAIN_DECAY_BASE = 0.15

SPEED_SKILL_MULTIPLIER = 1375.0
SPEED_STRAIN_DECAY_BASE = 0.3
SINGLE_SPACING_THRESHOLD = 125.0
MIN_SPEED_BONUS = 75.0

FL_SKILL_MULTIPLIER = 0.052
FL_STRAIN_DECAY_BASE = 0.15

STRAIN_DECAY_EXPONENT = 400.0
DECAY_WEIGHT = 0.94

@dataclass
class DiffHitObject:
    base: object
    pos: Vec2
    last_pos: Vec2
    last_last_pos: Vec2
    time: float
    delta_time: float
    strain_time: float

    jump_dist: float = 0.0
    travel_dist: float = 0.0
    movement_dist: float = 0.0
    angle: Optional[float] = None
    rhythm_complexity: float = 0.0

def _get_stacked_pos(obj) -> Vec2:
    return getattr(obj, "_stacked_pos", obj.pos)

def _build_diff_objects(
    hit_objects: list,
    clock_rate: float,
    cs: float,
) -> List[DiffHitObject]:
    if not hit_objects:
        return []

    scale_factor = NORMALIZED_RADIUS / (54.4 - 4.48 * cs)
    diff_objects: List[DiffHitObject] = []

    def norm(pos: Vec2) -> Vec2:
        return Vec2(pos.x * scale_factor, pos.y * scale_factor)

    last_pos = norm(_get_stacked_pos(hit_objects[0]))
    last_last_pos = last_pos

    for i, obj in enumerate(hit_objects):
        pos = norm(_get_stacked_pos(obj))
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
            ))
            last_last_pos = last_pos
            last_pos = pos
            continue

        prev = hit_objects[i - 1]
        prev_end_time = prev.end_time if isinstance(prev, Slider) else prev.time
        delta_time = (obj.time - prev_end_time) / clock_rate
        strain_time = max(delta_time, 25.0)

        dobj = DiffHitObject(
            base=obj,
            pos=pos,
            last_pos=last_pos,
            last_last_pos=last_last_pos,
            time=time,
            delta_time=delta_time,
            strain_time=strain_time,
        )

        if isinstance(prev, Slider):
            last_cursor = norm(_get_stacked_pos(prev))
            if prev.curve_points:
                last_cursor = norm(getattr(prev, "_stacked_pos", prev.curve_points[-1]))
            dobj.jump_dist = last_cursor.distance_to(pos)
            dobj.travel_dist = min(prev.lazy_travel_dist * scale_factor, MAXIMUM_SLIDER_RADIUS)
        else:
            dobj.jump_dist = last_pos.distance_to(pos)
            dobj.travel_dist = 0.0

        dobj.movement_dist = dobj.travel_dist + dobj.jump_dist

        if i >= 2:
            v1 = Vec2(last_last_pos.x - last_pos.x, last_last_pos.y - last_pos.y)
            v2 = Vec2(pos.x - last_pos.x, pos.y - last_pos.y)
            l1 = v1.length()
            l2 = v2.length()
            if l1 > 0 and l2 > 0:
                dot = max(-1.0, min(1.0, v1.dot(v2) / (l1 * l2)))
                dobj.angle = math.acos(dot)

        diff_objects.append(dobj)
        last_last_pos = last_pos
        last_pos = pos

    return diff_objects

def _evaluate_aim(curr: DiffHitObject, prev: DiffHitObject, with_sliders: bool) -> float:
    if isinstance(curr.base, Spinner):
        return 0.0

    curr_vel = curr.jump_dist / curr.strain_time
    if with_sliders and isinstance(prev.base, Slider):
        prev_vel = prev.travel_dist / prev.strain_time
        curr_vel = max(curr_vel, prev_vel)

    if curr.jump_dist == 0 and curr.travel_dist == 0:
        return 0.0

    wide_angle_bonus = 0.0
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

    strain_time = curr.strain_time
    great_window = 79.5 - curr.strain_time * 0.5

    dist = min(SINGLE_SPACING_THRESHOLD, curr.travel_dist + curr.jump_dist)
    delta_time = max(strain_time, great_window)

    speed_bonus = 0.0
    if strain_time < MIN_SPEED_BONUS:
        speed_bonus = 0.75 * math.pow((MIN_SPEED_BONUS - strain_time) / 40.0, 2)

    angle_bonus = 1.0
    if curr.angle is not None and curr.angle < math.pi / 2:
        angle_bonus = 1.0 + math.pow(math.sin(1.5 * (math.pi / 2 - curr.angle)), 2) * 0.3

    dist_bonus = math.pow(math.sin(math.pi / 2 * min(1.0, dist / SINGLE_SPACING_THRESHOLD)), 2)

    return (1.0 + speed_bonus) * angle_bonus * dist_bonus / strain_time

def _evaluate_flashlight(curr: DiffHitObject, hidden: bool) -> float:
    if isinstance(curr.base, Spinner):
        return 0.0

    scaling_factor = 52.0
    opacity_bonus = 1.0
    if hidden:
        opacity_bonus = 1.0 + 0.4 * min(1.0, curr.jump_dist / scaling_factor)

    return math.pow(0.8, max(0, curr.jump_dist / scaling_factor - 1)) * opacity_bonus

def _compute_skill_strains(
    diff_objects: List[DiffHitObject],
    evaluator,
    decay_base: float,
) -> List[float]:
    if not diff_objects:
        return []

    current_strain = 0.0
    strains: List[float] = []

    for i, curr in enumerate(diff_objects):
        if i == 0:
            strains.append(0.0)
            continue
        prev = diff_objects[i - 1]

        decay = math.pow(decay_base, curr.delta_time / 1000.0)
        current_strain *= decay
        current_strain += evaluator(curr, prev) * AIM_SKILL_MULTIPLIER \
            if evaluator.__name__ == "_evaluate_aim" else evaluator(curr)
        strains.append(current_strain)

    return strains

def _difficulty_value(strains: List[float], decay_weight: float = DECAY_WEIGHT) -> float:
    if not strains:
        return 0.0

    sorted_strains = sorted(strains, reverse=True)
    difficulty = 0.0
    weight = 1.0

    for strain in sorted_strains:
        difficulty += strain * weight
        weight *= decay_weight

    return difficulty

@dataclass
class DifficultyAttributes:
    stars: float = 0.0
    aim_difficulty: float = 0.0
    speed_difficulty: float = 0.0
    flashlight_difficulty: float = 0.0
    slider_factor: float = 1.0
    speed_note_count: float = 0.0
    aim_difficult_strain_count: float = 0.0
    speed_difficult_strain_count: float = 0.0
    approach_rate: float = 0.0
    overall_difficulty: float = 0.0
    drain_rate: float = 0.0
    hit_circle_count: int = 0
    slider_count: int = 0
    spinner_count: int = 0
    max_combo: int = 0

def calculate_difficulty(
    beatmap: Beatmap,
    mods: Mods = Mods.NM,
    clock_rate: Optional[float] = None,
    ar_override: Optional[float] = None,
    od_override: Optional[float] = None,
    cs_override: Optional[float] = None,
) -> DifficultyAttributes:
    cr = clock_rate or mods.speed_multiplier

    cs = min(10.0, (cs_override if cs_override is not None else beatmap.cs) * mods.cs_multiplier)
    ar_raw = (ar_override if ar_override is not None else beatmap.ar)
    od_raw = (od_override if od_override is not None else beatmap.od)

    ar = min(10.0, ar_raw * mods.ar_multiplier)
    od = min(10.0, od_raw * mods.od_multiplier)

    hit_objects = beatmap.hit_objects
    if not hit_objects:
        return DifficultyAttributes()

    diff_objects = _build_diff_objects(hit_objects, cr, cs)

    aim_strains_sliders: List[float] = []
    aim_strains_no_sliders: List[float] = []
    current_aim = 0.0
    current_aim_no_slider = 0.0

    for i, curr in enumerate(diff_objects):
        if i == 0:
            aim_strains_sliders.append(0.0)
            aim_strains_no_sliders.append(0.0)
            continue
        prev = diff_objects[i - 1]
        decay = math.pow(AIM_STRAIN_DECAY_BASE, curr.delta_time / 1000.0)
        current_aim = current_aim * decay + _evaluate_aim(curr, prev, True) * AIM_SKILL_MULTIPLIER
        current_aim_no_slider = current_aim_no_slider * decay + _evaluate_aim(curr, prev, False) * AIM_SKILL_MULTIPLIER
        aim_strains_sliders.append(current_aim)
        aim_strains_no_sliders.append(current_aim_no_slider)

    aim_diff = _difficulty_value(aim_strains_sliders)
    aim_diff_no_sliders = _difficulty_value(aim_strains_no_sliders)
    slider_factor = aim_diff_no_sliders / aim_diff if aim_diff > 0 else 1.0

    speed_strains: List[float] = []
    current_speed = 0.0
    for i, curr in enumerate(diff_objects):
        if i == 0:
            speed_strains.append(0.0)
            continue
        decay = math.pow(SPEED_STRAIN_DECAY_BASE, curr.delta_time / 1000.0)
        current_speed = current_speed * decay + _evaluate_speed(curr) * SPEED_SKILL_MULTIPLIER
        speed_strains.append(current_speed)

    speed_diff = _difficulty_value(speed_strains)

    speed_note_count = 0.0
    object_strains = sorted([s / 1375.0 for s in speed_strains if s > 0], reverse=True)
    if object_strains and object_strains[0] > 0:
        max_strain = object_strains[0]
        speed_note_count = sum(1.0 / (1.0 + math.exp(-(strain / max_strain * 12.0 - 6.0))) for strain in object_strains)

    aim_note_count = 0.0
    aim_object_strains = sorted(aim_strains_sliders, reverse=True)
    if aim_object_strains and aim_object_strains[0] > 0:
        max_aim = aim_object_strains[0]
        aim_note_count = sum(1.0 / (1.0 + math.exp(-(s / max_aim * 12.0 - 6.0))) for s in aim_object_strains)

    fl_diff = 0.0
    with_hidden = bool(mods & Mods.HD)
    if mods & Mods.FL:
        current_fl = 0.0
        fl_strains = []
        for i, curr in enumerate(diff_objects):
            if i == 0:
                fl_strains.append(0.0)
                continue
            decay = math.pow(FL_STRAIN_DECAY_BASE, curr.delta_time / 1000.0)
            current_fl = current_fl * decay + _evaluate_flashlight(curr, with_hidden) * FL_SKILL_MULTIPLIER
            fl_strains.append(current_fl)
        fl_diff = _difficulty_value(fl_strains)

    aim_stars = _scale_difficulty(aim_diff)
    speed_stars = _scale_difficulty(speed_diff)
    fl_stars = _scale_difficulty(fl_diff)

    stars = _star_rating(aim_stars, speed_stars, fl_stars)

    if ar < 5:
        ar_ms = 1800.0 - 120.0 * ar
    else:
        ar_ms = 1200.0 - 150.0 * (ar - 5.0)
    ar_ms /= cr
    ar_eff = (1800.0 - ar_ms) / 120.0 if ar_ms > 1200.0 else (1200.0 - ar_ms) / 150.0 + 5.0
    ar_eff = max(0.0, min(11.0, ar_eff))

    hit_window_300 = (80.0 - 6.0 * od) / cr
    od_eff = max(0.0, min(11.0, (80.0 - hit_window_300) / 6.0))

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

def _scale_difficulty(difficulty: float) -> float:
    if difficulty <= 0:
        return 0.0
    return difficulty * 0.0675

def _star_rating(aim: float, speed: float, fl: float) -> float:
    base = math.pow(math.pow(aim, 1.35) + math.pow(speed, 1.35), 1.0 / 1.35)
    if fl > 0:
        base = math.pow(math.pow(base, 1.1) + math.pow(fl * 0.4, 1.1), 1.0 / 1.1)
    return base * 1.03
