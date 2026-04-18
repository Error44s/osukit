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
from typing import Optional

from .beatmap import Beatmap as _Beatmap, Mods
from .difficulty import DifficultyAttributes, calculate_difficulty
from .performance import PerformanceAttributes, calculate_performance
from .taiko_difficulty import TaikoDifficultyAttributes, calculate_taiko_difficulty
from .taiko_performance import TaikoPerformanceAttributes, calculate_taiko_performance
from .models.scores import ScoreState


__all__ = [
    "Beatmap",
    "Difficulty",
    "Performance",
    "DifficultyAttributes",
    "PerformanceAttributes",
    "TaikoDifficultyAttributes",
    "TaikoPerformanceAttributes",
    "Mods",
    "GameMode",
    "ScoreState",
]


class GameMode:
    Osu = 0
    Taiko = 1
    Catch = 2
    Mania = 3


class Beatmap:
    def __init__(
        self,
        path: Optional[str] = None,
        content: Optional[str] = None,
        bytes: Optional[bytes] = None,
    ):
        from .beatmap import parse_beatmap
        if bytes is not None:
            content = bytes.decode("utf-8", errors="replace")
        self._inner = parse_beatmap(path=path, content=content)

    @property
    def title(self) -> str:
        return self._inner.title

    @property
    def artist(self) -> str:
        return self._inner.artist

    @property
    def mode(self) -> int:
        return self._inner.mode

    @property
    def n_circles(self) -> int:
        return self._inner.n_circles

    @property
    def n_sliders(self) -> int:
        return self._inner.n_sliders

    @property
    def n_spinners(self) -> int:
        return self._inner.n_spinners

    @property
    def n_objects(self) -> int:
        return self._inner.n_objects

    @property
    def max_combo(self) -> int:
        return self._inner.max_combo

    def __repr__(self) -> str:
        return (
            f"Beatmap(title={self.title!r}, circles={self.n_circles}, "
            f"sliders={self.n_sliders}, spinners={self.n_spinners})"
        )


class Difficulty:
    def __init__(
        self,
        mods: int = 0,
        clock_rate: Optional[float] = None,
        ar: Optional[float] = None,
        od: Optional[float] = None,
        cs: Optional[float] = None,
    ):
        self.mods = Mods(mods)
        self.clock_rate = clock_rate
        self.ar = ar
        self.od = od
        self.cs = cs

    def calculate(self, beatmap: "Beatmap"):
        mode = beatmap._inner.mode
        if mode == 0:
            return calculate_difficulty(
                beatmap._inner,
                mods=self.mods,
                clock_rate=self.clock_rate,
                ar_override=self.ar,
                od_override=self.od,
                cs_override=self.cs,
            )
        elif mode == 1:
            return calculate_taiko_difficulty(
                beatmap._inner,
                mods=self.mods,
                clock_rate=self.clock_rate,
                od_override=self.od,
            )
        raise NotImplementedError(f"Mode {mode} is not yet supported. Supported: 0 (Standard), 1 (Taiko).")

    def __repr__(self) -> str:
        return f"Difficulty(mods={self.mods!r}, clock_rate={self.clock_rate})"


class Performance:
    def __init__(
        self,
        mods: int = 0,
        accuracy: float = 100.0,
        combo: Optional[int] = None,
        misses: int = 0,
        n300: Optional[int] = None,
        n100: Optional[int] = None,
        n50: Optional[int] = None,
        slider_tick_miss: int = 0,
        slider_end_miss: int = 0,
        clock_rate: Optional[float] = None,
        tuning=None,
    ):
        self.mods = Mods(mods)
        self.accuracy = accuracy
        self.combo = combo
        self.misses = misses
        self.n300 = n300
        self.n100 = n100
        self.n50 = n50
        self.slider_tick_miss = slider_tick_miss
        self.slider_end_miss = slider_end_miss
        self.clock_rate = clock_rate
        self.tuning = tuning

    def calculate(self, beatmap_or_attrs, beatmap: Optional["Beatmap"] = None):
        if isinstance(beatmap_or_attrs, Beatmap):
            bm = beatmap_or_attrs._inner
            mode = bm.mode
            if mode == 1:
                return calculate_taiko_performance(
                    beatmap=bm,
                    mods=self.mods,
                    accuracy=self.accuracy,
                    combo=self.combo,
                    misses=self.misses,
                    n300=self.n300,
                    n100=self.n100,
                    clock_rate=self.clock_rate,
                )
            return calculate_performance(
                beatmap=bm,
                difficulty=None,
                mods=self.mods,
                accuracy=self.accuracy,
                combo=self.combo,
                misses=self.misses,
                n300=self.n300,
                n100=self.n100,
                n50=self.n50,
                slider_tick_miss=self.slider_tick_miss,
                slider_end_miss=self.slider_end_miss,
                clock_rate=self.clock_rate,
                tuning=self.tuning,
            )

        if isinstance(beatmap_or_attrs, _Beatmap):
            bm = beatmap_or_attrs
            mode = bm.mode
            if mode == 1:
                return calculate_taiko_performance(
                    beatmap=bm,
                    mods=self.mods,
                    accuracy=self.accuracy,
                    combo=self.combo,
                    misses=self.misses,
                    n300=self.n300,
                    n100=self.n100,
                    clock_rate=self.clock_rate,
                )
            return calculate_performance(
                beatmap=bm,
                difficulty=None,
                mods=self.mods,
                accuracy=self.accuracy,
                combo=self.combo,
                misses=self.misses,
                n300=self.n300,
                n100=self.n100,
                n50=self.n50,
                slider_tick_miss=self.slider_tick_miss,
                slider_end_miss=self.slider_end_miss,
                clock_rate=self.clock_rate,
                tuning=self.tuning,
            )

        if isinstance(beatmap_or_attrs, DifficultyAttributes):
            if beatmap is None:
                raise TypeError("When passing DifficultyAttributes directly, you must also provide beatmap=Beatmap(...).")
            return calculate_performance(
                beatmap=beatmap._inner,
                difficulty=beatmap_or_attrs,
                mods=self.mods,
                accuracy=self.accuracy,
                combo=self.combo,
                misses=self.misses,
                n300=self.n300,
                n100=self.n100,
                n50=self.n50,
                slider_tick_miss=self.slider_tick_miss,
                slider_end_miss=self.slider_end_miss,
                clock_rate=self.clock_rate,
                tuning=self.tuning,
            )

        if isinstance(beatmap_or_attrs, TaikoDifficultyAttributes):
            if beatmap is None:
                raise TypeError("When passing TaikoDifficultyAttributes directly, you must also provide beatmap=Beatmap(...).")
            return calculate_taiko_performance(
                beatmap=beatmap._inner,
                difficulty=beatmap_or_attrs,
                mods=self.mods,
                accuracy=self.accuracy,
                combo=self.combo,
                misses=self.misses,
                n300=self.n300,
                n100=self.n100,
                clock_rate=self.clock_rate,
            )

        raise TypeError(f"Expected Beatmap or DifficultyAttributes, got {type(beatmap_or_attrs)}")

    @classmethod
    def from_score_state(cls, score: ScoreState) -> "Performance":
        return cls(
            mods=score.mods,
            accuracy=score.accuracy(),
            combo=score.max_combo,
            misses=score.statistics.count_miss,
            n300=score.statistics.count_300,
            n100=score.statistics.count_100,
            n50=score.statistics.count_50,
            slider_tick_miss=score.statistics.slider_tick_miss,
            slider_end_miss=score.statistics.slider_end_miss,
        )

    def __repr__(self) -> str:
        return (
            f"Performance(mods={self.mods!r}, acc={self.accuracy}, "
            f"combo={self.combo}, misses={self.misses})"
        )
