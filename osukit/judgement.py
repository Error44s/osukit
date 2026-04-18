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
from typing import Iterable, Sequence

from .api import Beatmap
from .beatmap import Beatmap as CoreBeatmap, HitCircle, Slider, Spinner, Vec2, Mods
from .models import ScoreStatistics
from .replay import ReplayFrame

# Public data models
@dataclass
class SliderTickResult:
    tick_index: int
    tick_time_ms: float
    hit: bool
    frame_time_ms: float | None = None
    is_repeat_arrow: bool = False
    is_slider_end: bool = False


@dataclass
class SpinnerResult:
    rotations_completed: float
    rotations_required: float
    bonus_rotations: float
    completed: bool
    bonus_score: int


@dataclass
class JudgedObject:
    index: int
    kind: str # 'circle' | 'slider' | 'spinner'
    object_time_ms: float
    judgement: str # '300' | '100' | '50' | 'miss'
    hit_error_ms: float | None = None
    frame_time_ms: float | None = None
    combo_after: int = 0
    position_error: float | None = None

    # Slider-specific
    slider_head_hit: bool = True
    slider_ticks: list[SliderTickResult] = field(default_factory=list)
    sliderbreak: bool = False
    slider_end_hit: bool | None = None

    # Spinner-specific
    spinner_result: SpinnerResult | None = None


@dataclass
class JudgementReconstruction:
    mode: str
    object_index: int
    object_count: int
    progress: float
    statistics: ScoreStatistics
    max_combo: int
    max_combo_achieved: int
    fail_time_ms: float | None
    completed: bool
    objects: list[JudgedObject] = field(default_factory=list)
    unstable_rate: float | None = None
    mean_error_ms: float | None = None
    slider_tick_hits: int = 0
    slider_tick_total: int = 0
    slider_end_hits: int = 0
    slider_end_total: int = 0
    spinner_completion_ratio: float | None = None
    note: str | None = None

# Internal helpers
_KEY_MASK = 0xFF


def _normalise_beatmap(beatmap: Beatmap | CoreBeatmap) -> CoreBeatmap:
    return beatmap._inner if isinstance(beatmap, Beatmap) else beatmap


def _mods_obj(mods: int | Mods) -> Mods:
    return mods if isinstance(mods, Mods) else Mods(mods)


def _clock_rate(mods: int | Mods) -> float:
    return _mods_obj(mods).speed_multiplier


def _adjusted_od(base_od: float, mods: int | Mods) -> float:
    return max(0.0, min(10.0, base_od * _mods_obj(mods).od_multiplier))


def _hit_windows_std(od: float) -> tuple[float, float, float]:
    return (80.0 - 6.0 * od, 140.0 - 8.0 * od, 200.0 - 10.0 * od)


def _circle_radius(cs: float, mods: int | Mods) -> float:
    adj_cs = max(0.0, min(10.0, cs * _mods_obj(mods).cs_multiplier))
    return 54.4 - 4.48 * adj_cs


def _distance(a: Vec2, b: Vec2) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _key_press_frames(frames: Sequence[ReplayFrame]) -> list[ReplayFrame]:
    presses: list[ReplayFrame] = []
    prev = 0
    for frame in sorted(frames, key=lambda f: f.time_ms):
        keys = frame.keys & _KEY_MASK
        if keys and not prev:
            presses.append(frame)
        prev = keys
    return presses


def _cursor_at_time(frames: Sequence[ReplayFrame], time_ms: float) -> Vec2:
    sorted_f = sorted(frames, key=lambda f: f.time_ms)
    if not sorted_f:
        return Vec2(0.0, 0.0)
    if time_ms <= sorted_f[0].time_ms:
        return Vec2(sorted_f[0].x, sorted_f[0].y)
    if time_ms >= sorted_f[-1].time_ms:
        return Vec2(sorted_f[-1].x, sorted_f[-1].y)
    for i in range(len(sorted_f) - 1):
        a, b = sorted_f[i], sorted_f[i + 1]
        if a.time_ms <= time_ms <= b.time_ms:
            if b.time_ms == a.time_ms:
                return Vec2(a.x, a.y)
            t = (time_ms - a.time_ms) / (b.time_ms - a.time_ms)
            return Vec2(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
    return Vec2(sorted_f[-1].x, sorted_f[-1].y)


def _compute_slider_ticks(
    slider: Slider,
    timing_points: list,
    slider_tick_rate: float,
    rate: float,
) -> list[float]:
    ticks: list[float] = []
    if slider.repeats <= 0:
        return ticks
    beat_length = 500.0
    for tp in timing_points:
        if tp.time <= slider.time and getattr(tp, 'beat_length', 0) > 0:
            beat_length = tp.beat_length
    tick_interval = beat_length / max(slider_tick_rate, 0.001)
    span_duration = slider.duration / slider.repeats if slider.repeats > 0 else slider.duration
    for span in range(slider.repeats):
        span_start = slider.time + span * span_duration
        span_end = span_start + span_duration
        t = span_start + tick_interval
        while t < span_end - 10.0:
            ticks.append(t)
            t += tick_interval
    return sorted(ticks)


def _compute_repeat_arrow_times(slider: Slider) -> list[float]:
    if slider.repeats <= 1:
        return []
    times = []
    span_duration = slider.duration / slider.repeats if slider.repeats > 0 else slider.duration
    for i in range(1, slider.repeats):
        times.append(slider.time + i * span_duration)
    return times


def _rotations_for_spinner(spinner: Spinner, frames: Sequence[ReplayFrame], rate: float) -> float:
    window_start = spinner.time / rate
    window_end = spinner.end_time / rate
    center = Vec2(256.0, 192.0)
    sorted_f = [f for f in sorted(frames, key=lambda f: f.time_ms)
                if window_start - 50 <= f.time_ms <= window_end + 50]
    if len(sorted_f) < 2:
        return 0.0
    total_angle = 0.0
    prev_angle = None
    for frame in sorted_f:
        dx = frame.x - center.x
        dy = frame.y - center.y
        if abs(dx) < 1 and abs(dy) < 1:
            continue
        angle = math.atan2(dy, dx)
        if prev_angle is not None:
            delta = angle - prev_angle
            while delta > math.pi:
                delta -= 2 * math.pi
            while delta < -math.pi:
                delta += 2 * math.pi
            total_angle += abs(delta)
        prev_angle = angle
    return total_angle / (2 * math.pi)


def _spinner_rotations_required(spinner: Spinner, od: float, rate: float) -> float:
    duration_ms = (spinner.end_time - spinner.time) / rate
    base_rps = 3.0 + min(od, 10.0) * 0.1
    return max(1.0, base_rps * duration_ms / 1000.0)

# Main reconstruction
def reconstruct_judgements(
    beatmap: Beatmap | CoreBeatmap,
    replay_frames: Sequence[ReplayFrame] | Iterable[ReplayFrame],
    *,
    mods: int = 0,
    mode: str | None = None,
) -> JudgementReconstruction:
    bm = _normalise_beatmap(beatmap)
    mode_name = (mode or {0: 'osu', 1: 'taiko', 2: 'catch', 3: 'mania'}.get(bm.mode, 'osu')).lower()
    frames = sorted(list(replay_frames), key=lambda f: f.time_ms)

    if not frames:
        return JudgementReconstruction(
            mode=mode_name,
            object_index=0,
            object_count=len(bm.hit_objects),
            progress=0.0,
            statistics=ScoreStatistics(),
            max_combo=bm.max_combo,
            max_combo_achieved=0,
            fail_time_ms=None,
            completed=False,
            note='No replay frames provided.',
        )

    if mode_name != 'osu':
        last_time = max(f.time_ms for f in frames)
        object_index = 0
        for i, obj in enumerate(bm.hit_objects, start=1):
            end_time = getattr(obj, 'end_time', getattr(obj, 'time', 0.0))
            if end_time <= last_time:
                object_index = i
            else:
                break
        progress = (object_index / len(bm.hit_objects)) if bm.hit_objects else 0.0
        completed = bool(bm.hit_objects) and object_index >= len(bm.hit_objects)
        return JudgementReconstruction(
            mode=mode_name,
            object_index=object_index,
            object_count=len(bm.hit_objects),
            progress=progress,
            statistics=ScoreStatistics(count_300=object_index),
            max_combo=bm.max_combo,
            max_combo_achieved=min(object_index, bm.max_combo),
            fail_time_ms=None if completed else last_time,
            completed=completed,
            note=f'Preview reconstruction for {mode_name}. Full accuracy implemented for osu!standard only.',
        )

    rate = _clock_rate(mods)
    od = _adjusted_od(bm.od, mods)
    w300, w100, w50 = _hit_windows_std(od)
    radius = _circle_radius(bm.cs, mods) * 1.25

    presses = _key_press_frames(frames)
    used_presses: set[int] = set()

    judged: list[JudgedObject] = []
    errors: list[float] = []
    combo = 0
    max_combo_achieved = 0
    stats = ScoreStatistics()

    slider_tick_hits_total = 0
    slider_tick_total = 0
    slider_end_hits_total = 0
    slider_end_total = 0
    spinner_ratios: list[float] = []

    def find_press(target_time, pos=None, time_window=None):
        window = time_window if time_window is not None else w50 + 25.0
        best = None
        best_idx = None
        for idx, press in enumerate(presses):
            if idx in used_presses:
                continue
            actual_time = press.time_ms / rate
            delta = actual_time - target_time
            abs_delta = abs(delta)
            if abs_delta > window:
                continue
            pos_err = None
            if pos is not None:
                pos_err = _distance(Vec2(press.x, press.y), pos)
                if pos_err > radius:
                    continue
            candidate = (abs_delta, pos_err if pos_err is not None else 0.0, idx, press, delta)
            if best is None or candidate < best:
                best = candidate
                best_idx = idx
        if best is None:
            return None, None, None, None
        _, pos_err, idx, press, delta = best
        return press, delta, pos_err, idx

    for i, obj in enumerate(bm.hit_objects, start=1):
        obj_time = float(getattr(obj, 'time', 0.0))
        kind = (
            'circle' if isinstance(obj, HitCircle)
            else 'slider' if isinstance(obj, Slider)
            else 'spinner'
        )

        judgement = 'miss'
        hit_error = None
        frame_time_val = None
        position_error = None
        slider_head_hit = False
        slider_ticks: list[SliderTickResult] = []
        sliderbreak = False
        slider_end_hit: bool | None = None
        spinner_result: SpinnerResult | None = None

        # Spinner
        if isinstance(obj, Spinner):
            rotations = _rotations_for_spinner(obj, frames, rate)
            required = _spinner_rotations_required(obj, od, rate)
            bonus_rot = max(0.0, rotations - required)
            completed_spin = rotations >= required
            bonus_score = int(bonus_rot) * 1000

            spinner_result = SpinnerResult(
                rotations_completed=rotations,
                rotations_required=required,
                bonus_rotations=bonus_rot,
                completed=completed_spin,
                bonus_score=bonus_score,
            )
            spinner_ratios.append(min(1.0, rotations / required) if required > 0 else 1.0)

            if completed_spin:
                judgement = '300'
                combo += 1
                max_combo_achieved = max(max_combo_achieved, combo)
                stats.count_300 += 1
                frame_time_val = (obj_time + obj.end_time) / 2.0
                hit_error = 0.0
            else:
                judgement = 'miss'
                combo = 0
                stats.count_miss += 1

        # Slider
        elif isinstance(obj, Slider):
            press, delta, pos_err, press_idx = find_press(obj_time, obj.pos)
            if press is not None and delta is not None and press_idx is not None:
                used_presses.add(press_idx)
                slider_head_hit = True
                hit_error = delta
                frame_time_val = press.time_ms
                position_error = pos_err
                abs_delta = abs(delta)
                if abs_delta <= w300:
                    judgement = '300'
                elif abs_delta <= w100:
                    judgement = '100'
                elif abs_delta <= w50:
                    judgement = '50'
                else:
                    slider_head_hit = False
                    judgement = 'miss'
                if hit_error is not None and slider_head_hit:
                    errors.append(hit_error)

            end_time_ms = float(getattr(obj, 'end_time', obj_time))
            tick_times = _compute_slider_ticks(obj, bm.timing_points, bm.slider_tick_rate, rate)
            repeat_times = _compute_repeat_arrow_times(obj)

            sub_objects: list[tuple[float, bool]] = []
            for tt in tick_times:
                sub_objects.append((tt, False))
            for rt in repeat_times:
                sub_objects.append((rt, True))
            sub_objects.sort(key=lambda x: x[0])

            for sub_time, is_repeat in sub_objects:
                tick_window = 100.0
                any_key_near = any(
                    abs(f.time_ms - sub_time) <= tick_window and (f.keys & _KEY_MASK) != 0
                    for f in frames
                )
                tick_hit = slider_head_hit and any_key_near
                slider_ticks.append(SliderTickResult(
                    tick_index=len(slider_ticks),
                    tick_time_ms=sub_time,
                    hit=tick_hit,
                    frame_time_ms=sub_time if tick_hit else None,
                    is_repeat_arrow=is_repeat,
                    is_slider_end=False,
                ))
                slider_tick_total += 1
                if tick_hit:
                    slider_tick_hits_total += 1

            # Slider end
            slider_end_total += 1
            key_held_at_end = any(
                abs(f.time_ms - end_time_ms) <= 150 and (f.keys & _KEY_MASK) != 0
                for f in frames
            )
            if slider_head_hit:
                slider_end_hit = key_held_at_end
                if not key_held_at_end:
                    sliderbreak = True
                    combo = 0
                else:
                    slider_end_hits_total += 1
            else:
                slider_end_hit = False

            if slider_head_hit:
                if not sliderbreak:
                    combo += 1
                    max_combo_achieved = max(max_combo_achieved, combo)
                if judgement == '300':
                    stats.count_300 += 1
                elif judgement == '100':
                    stats.count_100 += 1
                elif judgement == '50':
                    stats.count_50 += 1
            else:
                combo = 0
                stats.count_miss += 1

            if slider_end_hit is False and slider_head_hit:
                stats.slider_end_miss += 1

        # HitCircle
        elif isinstance(obj, HitCircle):
            press, delta, pos_err, press_idx = find_press(obj_time, obj.pos)
            hit = False
            if press is not None and delta is not None and press_idx is not None:
                used_presses.add(press_idx)
                hit_error = delta
                frame_time_val = press.time_ms
                position_error = pos_err
                abs_delta = abs(delta)
                if abs_delta <= w300:
                    judgement = '300'
                    hit = True
                elif abs_delta <= w100:
                    judgement = '100'
                    hit = True
                elif abs_delta <= w50:
                    judgement = '50'
                    hit = True

            if hit:
                combo += 1
                max_combo_achieved = max(max_combo_achieved, combo)
                if judgement == '300':
                    stats.count_300 += 1
                elif judgement == '100':
                    stats.count_100 += 1
                elif judgement == '50':
                    stats.count_50 += 1
                if hit_error is not None:
                    errors.append(hit_error)
            else:
                combo = 0
                stats.count_miss += 1

        judged.append(JudgedObject(
            index=i,
            kind=kind,
            object_time_ms=obj_time,
            judgement=judgement,
            hit_error_ms=hit_error,
            frame_time_ms=frame_time_val,
            combo_after=combo,
            position_error=position_error,
            slider_head_hit=slider_head_hit if kind == 'slider' else True,
            slider_ticks=slider_ticks,
            sliderbreak=sliderbreak,
            slider_end_hit=slider_end_hit,
            spinner_result=spinner_result,
        ))

    last_time = max(f.time_ms for f in frames) / rate
    object_index = 0
    for obj in judged:
        if obj.object_time_ms <= last_time + w50:
            object_index = obj.index
        else:
            break

    completed = object_index >= len(bm.hit_objects) and len(bm.hit_objects) > 0
    progress = (object_index / len(bm.hit_objects)) if bm.hit_objects else 0.0

    mean_error = sum(errors) / len(errors) if errors else None
    unstable: float | None = None
    if errors:
        if len(errors) > 1:
            variance = sum((e - mean_error) ** 2 for e in errors) / len(errors)  # type: ignore
            unstable = math.sqrt(variance) * 10.0
        else:
            unstable = 0.0

    spinner_completion = (sum(spinner_ratios) / len(spinner_ratios)) if spinner_ratios else None

    return JudgementReconstruction(
        mode=mode_name,
        object_index=object_index,
        object_count=len(bm.hit_objects),
        progress=progress,
        statistics=stats,
        max_combo=bm.max_combo,
        max_combo_achieved=max_combo_achieved,
        fail_time_ms=None if completed else last_time,
        completed=completed,
        objects=judged,
        unstable_rate=unstable,
        mean_error_ms=mean_error,
        slider_tick_hits=slider_tick_hits_total,
        slider_tick_total=slider_tick_total,
        slider_end_hits=slider_end_hits_total,
        slider_end_total=slider_end_total,
        spinner_completion_ratio=spinner_completion,
    )
