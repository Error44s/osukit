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

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ScoreStatistics:
    count_300: int = 0
    count_100: int = 0
    count_50: int = 0
    count_miss: int = 0
    slider_tick_miss: int = 0
    slider_end_miss: int = 0
    geki: int = 0
    katu: int = 0

    @property
    def total_hits(self) -> int:
        return self.count_300 + self.count_100 + self.count_50 + self.count_miss + self.katu + self.geki

    def accuracy(self, mode: str = 'osu') -> float:
        mode = (mode or 'osu').lower()
        if mode in {'osu', 'fruits', 'catch'}:
            total = self.count_300 + self.count_100 + self.count_50 + self.count_miss + self.katu
            if total <= 0:
                return 100.0
            if mode in {'fruits', 'catch'}:
                caught = self.count_300 + self.count_100 + self.count_50
                return max(0.0, min(100.0, (caught / total) * 100.0))
            value = (6 * self.count_300 + 2 * self.count_100 + self.count_50) / (6 * total)
            return max(0.0, min(100.0, value * 100.0))
        if mode == 'taiko':
            total = self.count_300 + self.count_100 + self.count_miss
            if total <= 0:
                return 100.0
            value = (2 * self.count_300 + self.count_100) / (2 * total)
            return max(0.0, min(100.0, value * 100.0))
        if mode == 'mania':
            total = self.count_300 + self.count_100 + self.count_50 + self.count_miss + self.katu + self.geki
            if total <= 0:
                return 100.0
            value = (320 * self.count_50 + 300 * self.count_100 + 200 * self.katu + 300 * self.count_300 + 305 * self.geki) / (305 * total)
            return max(0.0, min(100.0, value * 100.0))
        return self.accuracy('osu')

    @classmethod
    def from_api_v2(cls, data: dict[str, Any] | None) -> 'ScoreStatistics':
        data = data or {}
        return cls(
            count_300=int(data.get('count_300', 0) or 0),
            count_100=int(data.get('count_100', 0) or 0),
            count_50=int(data.get('count_50', 0) or 0),
            count_miss=int(data.get('count_miss', 0) or 0),
            slider_tick_miss=int(data.get('slider_tail_hit', 0) or 0),
            slider_end_miss=int(data.get('large_tick_miss', 0) or 0),
            geki=int(data.get('count_geki', 0) or 0),
            katu=int(data.get('count_katu', 0) or 0),
        )


@dataclass
class BeatmapRef:
    id: Optional[int] = None
    beatmapset_id: Optional[int] = None
    artist: Optional[str] = None
    title: Optional[str] = None
    version: Optional[str] = None
    mode: Optional[str] = None
    url: Optional[str] = None
    max_combo: Optional[int] = None
    stars: Optional[float] = None
    bpm: Optional[float] = None
    ar: Optional[float] = None
    od: Optional[float] = None
    cs: Optional[float] = None
    hp: Optional[float] = None
    total_length: Optional[int] = None
    status: Optional[str] = None
    cover_url: Optional[str] = None

    @classmethod
    def from_api_v2(cls, data: dict[str, Any] | None) -> 'BeatmapRef':
        data = data or {}
        beatmapset = data.get('beatmapset') or {}
        covers = beatmapset.get('covers') or {}
        return cls(
            id=_to_int(data.get('id')),
            beatmapset_id=_to_int(data.get('beatmapset_id')),
            artist=beatmapset.get('artist') or data.get('artist'),
            title=beatmapset.get('title') or data.get('title'),
            version=data.get('version'),
            mode=data.get('mode'),
            url=data.get('url'),
            max_combo=_to_int(data.get('max_combo')),
            stars=_to_float(data.get('difficulty_rating')),
            bpm=_to_float(data.get('bpm')),
            ar=_to_float(data.get('ar')),
            od=_to_float(data.get('accuracy')),
            cs=_to_float(data.get('cs')),
            hp=_to_float(data.get('drain')),
            total_length=_to_int(data.get('total_length')),
            status=data.get('status') or beatmapset.get('status'),
            cover_url=covers.get('card') or covers.get('cover'),
        )


@dataclass
class UserRef:
    id: Optional[int] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    country_code: Optional[str] = None

    @classmethod
    def from_api_v2(cls, data: dict[str, Any] | None) -> 'UserRef':
        data = data or {}
        return cls(
            id=_to_int(data.get('id')),
            username=data.get('username'),
            avatar_url=data.get('avatar_url'),
            country_code=data.get('country_code'),
        )


@dataclass
class ScoreState:
    mods: int = 0
    mods_list: list[str] = field(default_factory=list)
    max_combo: Optional[int] = None
    statistics: ScoreStatistics = field(default_factory=ScoreStatistics)
    passed: bool = True
    rank: Optional[str] = None
    score: Optional[int] = None
    legacy_score: Optional[int] = None
    pp: Optional[float] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    beatmap_id: Optional[int] = None
    beatmapset_id: Optional[int] = None
    created_at: Optional[str] = None
    ended_at: Optional[str] = None
    mode: Optional[str] = None
    replay_available: Optional[bool] = None
    is_perfect_combo: Optional[bool] = None
    beatmap: BeatmapRef = field(default_factory=BeatmapRef)
    user: UserRef = field(default_factory=UserRef)
    raw: dict[str, Any] = field(default_factory=dict)

    def accuracy(self) -> float:
        return self.statistics.accuracy(self.mode or self.beatmap.mode or 'osu')

    @classmethod
    def from_api_v2(cls, data: dict[str, Any]) -> 'ScoreState':
        mods_list = [str(m) for m in (data.get('mods') or [])]
        user_payload = data.get('user') or {}
        beatmap_payload = data.get('beatmap') or {}
        mode = data.get('mode') or beatmap_payload.get('mode')
        return cls(
            mods=int(data.get('mods_int', 0) or 0),
            mods_list=mods_list,
            max_combo=int(data.get('max_combo', 0) or 0),
            statistics=ScoreStatistics.from_api_v2(data.get('statistics', {})),
            passed=bool(data.get('passed', False)),
            rank=data.get('rank'),
            score=_to_int(data.get('score')),
            legacy_score=_to_int(data.get('legacy_total_score') or data.get('legacy_score')),
            pp=_to_float(data.get('pp')),
            user_id=_to_int(data.get('user_id') or user_payload.get('id')),
            username=user_payload.get('username'),
            beatmap_id=_to_int(data.get('beatmap_id') or beatmap_payload.get('id')),
            beatmapset_id=_to_int(beatmap_payload.get('beatmapset_id')),
            created_at=data.get('created_at'),
            ended_at=data.get('ended_at'),
            mode=mode,
            replay_available=data.get('replay') if isinstance(data.get('replay'), bool) else data.get('replay_available'),
            is_perfect_combo=data.get('perfect') if isinstance(data.get('perfect'), bool) else data.get('is_perfect_combo'),
            beatmap=BeatmapRef.from_api_v2(beatmap_payload),
            user=UserRef.from_api_v2(user_payload),
            raw=dict(data),
        )


@dataclass
class PartialPlaySnapshot:
    object_index: int
    object_count: int
    progress: float
    combo: int
    statistics: ScoreStatistics
    estimated_max_combo_at_progress: int
    passed: bool = False

    def accuracy(self, mode: str = 'osu') -> float:
        return self.statistics.accuracy(mode)


@dataclass
class ProjectedScore:
    snapshot: PartialPlaySnapshot
    current_pp: float | None
    if_fc_pp: float | None
    map_completion_text: str
    estimated_full_combo_pp: float | None = 0.0
    choke_pp: float | None = 0.0
    partial_max_combo: int = 0




@dataclass
class PaceMetrics:
    elapsed_time_ms: float | None = None
    objects_per_second: float | None = None
    combo_per_second: float | None = None
    current_pp_per_second: float | None = None


@dataclass
class AnalyzedScore:
    score: ScoreState
    snapshot: PartialPlaySnapshot
    current_pp: float | None
    if_fc_pp: float | None
    choke_pp: float | None
    estimated_full_combo_pp: float | None
    partial_max_combo: int
    full_max_combo: int
    map_completion_text: str
    analysis_source: str = 'local'
    replay_cursor: Any = None
    replay_reconstruction: Any = None
    pace: PaceMetrics | None = None

    @property
    def passed(self) -> bool:
        return self.score.passed

    @property
    def accuracy(self) -> float:
        return self.score.accuracy()


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
