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
from enum import IntFlag
from typing import List, Optional, Tuple

# Mod Flags (bitwise, same as osu! API)
class Mods(IntFlag):
    NM  = 0
    NF  = 1 << 0   # No Fail
    EZ  = 1 << 1   # Easy
    TD  = 1 << 2   # TouchDevice
    HD  = 1 << 3   # Hidden
    HR  = 1 << 4   # Hard Rock
    SD  = 1 << 5   # Sudden Death
    DT  = 1 << 6   # Double Time
    RX  = 1 << 7   # Relax
    HT  = 1 << 8   # Half Time
    NC  = 1 << 9   # Nightcore (implies DT)
    FL  = 1 << 10  # Flashlight
    AT  = 1 << 11  # Auto
    SO  = 1 << 12  # SpunOut
    AP  = 1 << 13  # Autopilot
    PF  = 1 << 14  # Perfect
    KEY4 = 1 << 15
    KEY5 = 1 << 16
    KEY6 = 1 << 17
    KEY7 = 1 << 18
    KEY8 = 1 << 19
    FI  = 1 << 20  # FadeIn
    RN  = 1 << 21  # Random
    CN  = 1 << 22  # Cinema
    TP  = 1 << 23  # Target Practice
    KEY9 = 1 << 24
    COOP = 1 << 25
    KEY1 = 1 << 26
    KEY3 = 1 << 27
    KEY2 = 1 << 28
    SV2 = 1 << 29  # ScoreV2
    MR  = 1 << 30  # Mirror

    @property
    def speed_multiplier(self) -> float:
        if self & Mods.DT or self & Mods.NC:
            return 1.5
        if self & Mods.HT:
            return 0.75
        return 1.0

    @property
    def od_multiplier(self) -> float:
        if self & Mods.HR:
            return 1.4
        if self & Mods.EZ:
            return 0.5
        return 1.0

    @property
    def ar_multiplier(self) -> float:
        if self & Mods.HR:
            return 1.4
        if self & Mods.EZ:
            return 0.5
        return 1.0

    @property
    def cs_multiplier(self) -> float:
        if self & Mods.HR:
            return 1.3
        if self & Mods.EZ:
            return 0.5
        return 1.0

# Data classes
@dataclass
class Vec2:
    x: float
    y: float

    def distance_to(self, other: "Vec2") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalize(self) -> "Vec2":
        l = self.length()
        if l == 0:
            return Vec2(0, 0)
        return Vec2(self.x / l, self.y / l)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y


@dataclass
class TimingPoint:
    time: float          # ms
    beat_length: float   # ms per beat (positive = uninherited, negative = inherited/slider velocity)
    meter: int           # time signature numerator
    is_uninherited: bool

    @property
    def bpm(self) -> float:
        if self.beat_length > 0:
            return 60000.0 / self.beat_length
        return 0.0

    @property
    def slider_velocity_multiplier(self) -> float:
        """For inherited points: -100 / beat_length"""
        if not self.is_uninherited and self.beat_length < 0:
            return -100.0 / self.beat_length
        return 1.0


@dataclass
class HitCircle:
    pos: Vec2
    time: float # ms
    combo_index: int = 0
    stack_height: int = 0


@dataclass
class SliderCurvePoint:
    pos: Vec2


@dataclass
class Slider:
    pos: Vec2
    time: float # ms
    end_time: float = 0.0
    pixel_length: float = 0.0
    repeats: int = 1
    curve_type: str = "L"
    curve_points: List[Vec2] = field(default_factory=list)
    tick_count: int = 0
    combo_index: int = 0
    stack_height: int = 0
    lazy_end_pos: Vec2 = field(default_factory=lambda: Vec2(0, 0))
    lazy_travel_dist: float = 0.0

    @property
    def duration(self) -> float:
        return self.end_time - self.time

    @property
    def span_duration(self) -> float:
        if self.repeats > 0:
            return self.duration / self.repeats
        return self.duration

@dataclass
class Spinner:
    pos: Vec2
    time: float
    end_time: float
    combo_index: int = 0

HitObject = HitCircle | Slider | Spinner

@dataclass
class Beatmap:
    # Metadata
    title: str = ""
    artist: str = ""
    creator: str = ""
    version: str = ""
    mode: int = 0 # 0=std, 1=taiko, 2=ctb, 3=mania

    # Difficulty
    hp: float = 5.0
    cs: float = 5.0
    od: float = 5.0
    ar: float = 5.0
    slider_multiplier: float = 1.4
    slider_tick_rate: float = 1.0

    # Objects
    hit_objects: List[HitObject] = field(default_factory=list)
    timing_points: List[TimingPoint] = field(default_factory=list)

    @property
    def n_circles(self) -> int:
        return sum(1 for o in self.hit_objects if isinstance(o, HitCircle))

    @property
    def n_sliders(self) -> int:
        return sum(1 for o in self.hit_objects if isinstance(o, Slider))

    @property
    def n_spinners(self) -> int:
        return sum(1 for o in self.hit_objects if isinstance(o, Spinner))

    @property
    def n_objects(self) -> int:
        return len(self.hit_objects)

    @property
    def max_combo(self) -> int:
        combo = 0
        for obj in self.hit_objects:
            if isinstance(obj, HitCircle):
                combo += 1
            elif isinstance(obj, Slider):
                combo += 1 + obj.tick_count + (obj.repeats - 1) + 1
            elif isinstance(obj, Spinner):
                combo += 1
        return combo

    def get_beat_length_at(self, time: float) -> float:
        """Returns the uninherited beat length (ms/beat) at given time."""
        result = 500.0  # default 120 BPM
        for tp in self.timing_points:
            if tp.time <= time and tp.is_uninherited:
                result = tp.beat_length
        return result

    def get_slider_velocity_at(self, time: float) -> float:
        """Returns effective slider velocity multiplier at given time."""
        sv = 1.0
        for tp in self.timing_points:
            if tp.time <= time and not tp.is_uninherited:
                sv = tp.slider_velocity_multiplier
        return sv

# Parser
def _parse_vec2(s: str) -> Vec2:
    parts = s.split(",")
    return Vec2(float(parts[0]), float(parts[1]))


def _calculate_slider_end_time(
    slider: Slider,
    beat_length: float,
    base_sv: float,
    sv_multiplier: float,
    tick_rate: float,
) -> Tuple[float, int]:
    """Returns (end_time, tick_count)."""
    if beat_length <= 0:
        beat_length = 500.0
    effective_sv = base_sv * sv_multiplier * 100.0
    # duration in ms for one span
    duration_per_span = (slider.pixel_length / effective_sv) * beat_length
    end_time = slider.time + duration_per_span * slider.repeats

    # tick count (excluding head/tail)
    tick_distance = effective_sv / tick_rate
    if tick_distance > 0:
        spans = slider.repeats
        span_ticks = max(0, math.floor(slider.pixel_length / tick_distance) - 1)
        tick_count = span_ticks * spans + (spans - 1)
    else:
        tick_count = 0

    return end_time, tick_count


def parse_beatmap(path: str | None = None, content: str | None = None) -> Beatmap:
    """Parse a .osu file from path or raw content string."""
    if path is not None:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
    if content is None:
        raise ValueError("Either path or content must be provided.")

    bm = Beatmap()
    section = ""
    lines = content.splitlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue

        if section == "Metadata":
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if key == "Title":
                    bm.title = val
                elif key == "Artist":
                    bm.artist = val
                elif key == "Creator":
                    bm.creator = val
                elif key == "Version":
                    bm.version = val

        elif section == "General":
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if key == "Mode":
                    bm.mode = int(val)

        elif section == "Difficulty":
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if key == "HPDrainRate":
                    bm.hp = float(val)
                elif key == "CircleSize":
                    bm.cs = float(val)
                elif key == "OverallDifficulty":
                    bm.od = float(val)
                elif key == "ApproachRate":
                    bm.ar = float(val)
                elif key == "SliderMultiplier":
                    bm.slider_multiplier = float(val)
                elif key == "SliderTickRate":
                    bm.slider_tick_rate = float(val)

        elif section == "TimingPoints":
            parts = line.split(",")
            if len(parts) < 2:
                continue
            try:
                time = float(parts[0])
                beat_length = float(parts[1])
                meter = int(parts[2]) if len(parts) > 2 else 4
                is_uninherited = (int(parts[6]) == 1) if len(parts) > 6 else (beat_length > 0)
                bm.timing_points.append(TimingPoint(time, beat_length, meter, is_uninherited))
            except (ValueError, IndexError):
                continue

        elif section == "HitObjects":
            parts = line.split(",")
            if len(parts) < 4:
                continue
            try:
                x = float(parts[0])
                y = float(parts[1])
                time = float(parts[2])
                obj_type = int(parts[3])

                pos = Vec2(x, y)

                # type bits: 0=circle, 1=slider, 3=spinner
                if obj_type & 2:  # slider
                    curve_info = parts[5] if len(parts) > 5 else "L|0:0"
                    curve_parts = curve_info.split("|")
                    curve_type = curve_parts[0] if curve_parts else "L"
                    curve_points = [pos]
                    for cp in curve_parts[1:]:
                        cp_parts = cp.split(":")
                        if len(cp_parts) == 2:
                            curve_points.append(Vec2(float(cp_parts[0]), float(cp_parts[1])))

                    repeats = int(parts[6]) if len(parts) > 6 else 1
                    pixel_length = float(parts[7]) if len(parts) > 7 else 100.0

                    # Find beat length and sv at this time
                    beat_length = bm.get_beat_length_at(time)
                    sv_mult = bm.get_slider_velocity_at(time)

                    end_time, tick_count = _calculate_slider_end_time(
                        Slider(pos=pos, time=time, pixel_length=pixel_length, repeats=repeats),
                        beat_length,
                        bm.slider_multiplier,
                        sv_mult,
                        bm.slider_tick_rate,
                    )

                    slider = Slider(
                        pos=pos,
                        time=time,
                        end_time=end_time,
                        pixel_length=pixel_length,
                        repeats=repeats,
                        curve_type=curve_type,
                        curve_points=curve_points,
                        tick_count=tick_count,
                    )
                    bm.hit_objects.append(slider)

                elif obj_type & 8:  # spinner
                    end_time = float(parts[5]) if len(parts) > 5 else time + 1000
                    bm.hit_objects.append(Spinner(pos=pos, time=time, end_time=end_time))

                else:  # circle
                    bm.hit_objects.append(HitCircle(pos=pos, time=time))

            except (ValueError, IndexError):
                continue

    # Sort by time (should already be sorted, but just in case)
    bm.hit_objects.sort(key=lambda o: o.time)

    # Apply stacking
    _apply_stacking(bm)

    return bm


def _apply_stacking(bm: Beatmap, stack_distance: float = 3.0):
    """Simplified stack offset calculation for osu! standard."""
    STACK_LENIENCY = 0.7
    if not bm.hit_objects:
        return

    # AR to preempt time
    ar = bm.ar
    if ar < 5:
        preempt = 1200.0 + 600.0 * (5.0 - ar) / 5.0
    elif ar > 5:
        preempt = 1200.0 - 750.0 * (ar - 5.0) / 5.0
    else:
        preempt = 1200.0

    stack_threshold = preempt * STACK_LENIENCY

    n = len(bm.hit_objects)
    stack_heights = [0] * n

    for i in range(n - 1, -1, -1):
        stack_base = i
        for n2 in range(stack_base + 1, n):
            obj_i = bm.hit_objects[stack_base]
            obj_n2 = bm.hit_objects[n2]

            if obj_n2.time - obj_i.time > stack_threshold:
                break

            end_pos_i = obj_i.pos
            if isinstance(obj_i, Slider):
                end_pos_i = obj_i.curve_points[-1] if obj_i.curve_points else obj_i.pos

            if end_pos_i.distance_to(obj_n2.pos) < stack_distance:
                stack_heights[stack_base] = stack_heights[n2] + 1
                break

            if isinstance(obj_i, Slider) and obj_i.pos.distance_to(obj_n2.pos) < stack_distance:
                offset = stack_heights[stack_base] - stack_heights[n2] + 1
                for j in range(n2, stack_base - 1, -1):
                    if obj_i.pos.distance_to(bm.hit_objects[j].pos) < stack_distance:
                        stack_heights[j] -= offset
                break

    cs_scale = (1.0 - 0.7 * (bm.cs - 5.0) / 5.0) / 2.0
    for i, obj in enumerate(bm.hit_objects):
        h = stack_heights[i]
        if isinstance(obj, HitCircle):
            obj.stack_height = h
        elif isinstance(obj, Slider):
            obj.stack_height = h

    def stacked_pos(obj: HitObject) -> Vec2:
        h = getattr(obj, "stack_height", 0)
        offset = h * cs_scale * -6.4
        return Vec2(obj.pos.x + offset, obj.pos.y + offset)

    # Store stacked positions for difficulty calculation
    for obj in bm.hit_objects:
        obj._stacked_pos = stacked_pos(obj)  # type: ignore[attr-defined]
