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

from .models import AnalyzedScore, BeatmapRef


def _fmt_pp(value: float | None) -> str:
    return '-' if value is None else f'{value:.2f}pp'


def _fmt_acc(value: float) -> str:
    return f'{value:.2f}%'


def _beatmap_title(beatmap: Any) -> str:
    return f'{getattr(beatmap, "artist", None) or "Unknown"} - {getattr(beatmap, "title", None) or "Unknown"}'


@dataclass
class ProfileResult:
    raw: dict[str, Any]
    user_id: Optional[int]
    username: str
    avatar_url: Optional[str]
    country_code: Optional[str]
    pp: Optional[float]
    global_rank: Optional[int]
    country_rank: Optional[int]
    play_count: Optional[int]
    accuracy: Optional[float]
    level: Optional[float]

    @property
    def profile_url(self) -> Optional[str]:
        return None if self.user_id is None else f'https://osu.ppy.sh/users/{self.user_id}'

    @classmethod
    def from_api_v2(cls, payload: dict[str, Any]) -> 'ProfileResult':
        stats = payload.get('statistics') or {}
        level_payload = stats.get('level') or {}
        level_current = level_payload.get('current')
        level_progress = level_payload.get('progress')
        level = None
        if level_current is not None:
            level = float(level_current)
            if level_progress is not None:
                level += float(level_progress) / 100.0
        return cls(
            raw=dict(payload),
            user_id=_to_int(payload.get('id')),
            username=str(payload.get('username') or payload.get('id') or 'Unknown'),
            avatar_url=payload.get('avatar_url'),
            country_code=payload.get('country_code'),
            pp=_to_float(stats.get('pp')),
            global_rank=_to_int(stats.get('global_rank')),
            country_rank=_to_int(stats.get('country_rank')),
            play_count=_to_int(stats.get('play_count')),
            accuracy=_to_float(stats.get('hit_accuracy')),
            level=level,
        )

    def to_embed_payload(self, *, color: int | None = None) -> dict[str, Any]:
        fields = [
            {'name': 'PP', 'value': _fmt_pp(self.pp), 'inline': True},
            {'name': 'Accuracy', 'value': '-' if self.accuracy is None else _fmt_acc(self.accuracy), 'inline': True},
            {'name': 'Level', 'value': '-' if self.level is None else f'{self.level:.2f}', 'inline': True},
            {'name': 'Global Rank', 'value': '-' if self.global_rank is None else f'#{self.global_rank:,}', 'inline': True},
            {'name': 'Country Rank', 'value': '-' if self.country_rank is None else f'#{self.country_rank:,}', 'inline': True},
            {'name': 'Play Count', 'value': '-' if self.play_count is None else f'{self.play_count:,}', 'inline': True},
        ]
        payload = {
            'title': self.username,
            'description': f'osu! profile{f" ({self.country_code})" if self.country_code else ""}',
            'fields': fields,
            'thumbnail': {'url': self.avatar_url} if self.avatar_url else None,
            'url': self.profile_url,
        }
        if color is not None:
            payload['color'] = color
        return payload


@dataclass
class MapResult:
    raw: dict[str, Any]
    beatmap: BeatmapRef

    @property
    def url(self) -> Optional[str]:
        return self.beatmap.url

    @classmethod
    def from_api_v2(cls, payload: dict[str, Any]) -> 'MapResult':
        return cls(raw=dict(payload), beatmap=BeatmapRef.from_api_v2(payload))

    def to_embed_payload(self, *, color: int | None = None) -> dict[str, Any]:
        fields = [
            {'name': 'Stars', 'value': '-' if self.beatmap.stars is None else f'{self.beatmap.stars:.2f}★', 'inline': True},
            {'name': 'Length', 'value': '-' if self.beatmap.total_length is None else f'{self.beatmap.total_length}s', 'inline': True},
            {'name': 'BPM', 'value': '-' if self.beatmap.bpm is None else f'{self.beatmap.bpm:.0f}', 'inline': True},
            {'name': 'Stats', 'value': f'AR {self.beatmap.ar or 0:.1f} • OD {self.beatmap.od or 0:.1f} • CS {self.beatmap.cs or 0:.1f} • HP {self.beatmap.hp or 0:.1f}', 'inline': False},
        ]
        payload = {
            'title': _beatmap_title(self.beatmap),
            'description': f'[{self.beatmap.version or "?"}] • {self.beatmap.mode or "osu"} • {self.beatmap.status or "unknown"}',
            'fields': fields,
            'url': self.url,
        }
        if self.beatmap.cover_url:
            payload['thumbnail'] = {'url': self.beatmap.cover_url}
        if color is not None:
            payload['color'] = color
        return payload


@dataclass
class PlayResult:
    kind: str
    user_query: str | int
    beatmap: Any
    api_score: dict[str, Any]
    analysis: AnalyzedScore
    profile: ProfileResult | None = None

    @property
    def score(self):
        return self.analysis.score

    @property
    def passed(self) -> bool:
        return self.analysis.passed

    @property
    def beatmap_url(self) -> Optional[str]:
        return getattr(self.score.beatmap, 'url', None) or self.api_score.get('beatmap', {}).get('url')

    @property
    def mode(self) -> str:
        return self.score.mode or getattr(self.score.beatmap, 'mode', None) or 'osu'

    def to_embed_payload(self, *, color: int | None = None) -> dict[str, Any]:
        from .bot import build_embed_payload
        payload = build_embed_payload(self.analysis, self.beatmap, self.api_score, color=color)
        if self.beatmap_url and 'url' not in payload:
            payload['url'] = self.beatmap_url
        return payload

    def to_markdown(self) -> str:
        from .bot import format_analysis_markdown
        return format_analysis_markdown(self.analysis, self.beatmap, self.api_score)


@dataclass
class PlayListResult:
    kind: str
    user_query: str | int
    plays: list[PlayResult] = field(default_factory=list)
    profile: ProfileResult | None = None

    def to_compact_lines(self) -> list[str]:
        lines: list[str] = []
        for idx, play in enumerate(self.plays, start=1):
            beatmap = play.beatmap
            score = play.score
            lines.append(
                f'{idx}. {beatmap.artist} - {beatmap.title} | {score.rank or "?"} | '
                f'{score.accuracy():.2f}% | {_fmt_pp(play.analysis.current_pp)}'
            )
        return lines

    def to_embed_payload(self, *, color: int | None = None) -> dict[str, Any]:
        desc = '\n'.join(self.to_compact_lines()) or 'No plays found.'
        if self.profile and self.profile.username:
            desc = f'User: {self.profile.username}\n\n' + desc
        payload = {'title': f'{self.kind.title()} plays', 'description': desc, 'fields': []}
        if color is not None:
            payload['color'] = color
        if self.profile and self.profile.avatar_url:
            payload['thumbnail'] = {'url': self.profile.avatar_url}
        if self.profile and self.profile.profile_url:
            payload['url'] = self.profile.profile_url
        return payload


@dataclass
class CompareResult:
    beatmap: Any
    left: PlayResult
    right: PlayResult

    def winner_by_pp(self) -> PlayResult | None:
        lpp = self.left.analysis.current_pp or 0.0
        rpp = self.right.analysis.current_pp or 0.0
        if lpp == rpp:
            return None
        return self.left if lpp > rpp else self.right

    def to_embed_payload(self, *, color: int | None = None) -> dict[str, Any]:
        winner = self.winner_by_pp()
        winner_text = 'Tie' if winner is None else f'{winner.score.username or winner.user_query} leads by PP'
        fields = [
            {
                'name': str(self.left.score.username or self.left.user_query),
                'value': (
                    f'Acc: {_fmt_acc(self.left.score.accuracy())}\n'
                    f'PP: {_fmt_pp(self.left.analysis.current_pp)}\n'
                    f'Combo: {self.left.score.max_combo or 0}x'
                ),
                'inline': True,
            },
            {
                'name': str(self.right.score.username or self.right.user_query),
                'value': (
                    f'Acc: {_fmt_acc(self.right.score.accuracy())}\n'
                    f'PP: {_fmt_pp(self.right.analysis.current_pp)}\n'
                    f'Combo: {self.right.score.max_combo or 0}x'
                ),
                'inline': True,
            },
        ]
        payload = {'title': _beatmap_title(self.beatmap), 'description': winner_text, 'fields': fields}
        if color is not None:
            payload['color'] = color
        beatmap_url = getattr(self.left, 'beatmap_url', None) or getattr(self.right, 'beatmap_url', None)
        if beatmap_url:
            payload['url'] = beatmap_url
        return payload


def _to_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
