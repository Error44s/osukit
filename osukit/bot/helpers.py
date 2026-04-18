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

from typing import Any, Optional, Sequence

from ..api import Beatmap
from ..errors import MissingBeatmapError
from ..live import analyze_api_score
from ..models.scores import AnalyzedScore, ScoreState
from ..resolver import BeatmapResolver
from ..replay import ReplayFrame

MOD_BIT_NAMES = [
    (1 << 9, 'NC'),
    (1 << 6, 'DT'),
    (1 << 8, 'HT'),
    (1 << 3, 'HD'),
    (1 << 4, 'HR'),
    (1 << 1, 'EZ'),
    (1 << 10, 'FL'),
    (1 << 14, 'PF'),
    (1 << 5, 'SD'),
    (1 << 0, 'NF'),
    (1 << 12, 'SO'),
]


def format_mods(mods: int, mods_list: Optional[list[str]] = None) -> str:
    if mods_list:
        normalized = [str(m).upper() for m in mods_list]
        if 'NC' in normalized and 'DT' in normalized:
            normalized = [m for m in normalized if m != 'DT']
        if 'PF' in normalized and 'SD' in normalized:
            normalized = [m for m in normalized if m != 'SD']
        return ''.join(normalized) or 'NM'
    if not mods:
        return 'NM'
    names = [name for bit, name in MOD_BIT_NAMES if mods & bit]
    if 'NC' in names and 'DT' in names:
        names.remove('DT')
    if 'PF' in names and 'SD' in names:
        names.remove('SD')
    return ''.join(names) or 'NM'


def parse_mods(mods: list[str] | str | None) -> list[str]:
    if mods is None:
        return []
    if isinstance(mods, str):
        mods = [mods[i:i+2] for i in range(0, len(mods), 2)]
    return [str(m).upper() for m in mods if m]


def mods_to_int(mods: list[str] | str | None) -> int:
    mapping = {name: bit for bit, name in MOD_BIT_NAMES}
    value = 0
    for mod in parse_mods(mods):
        value |= mapping.get(mod, 0)
    if value & (1 << 9): # NC implies DT
        value |= (1 << 6)
    if value & (1 << 14): # PF implies SD
        value |= (1 << 5)
    return value


def extract_beatmap_id(api_score: dict[str, Any]) -> Optional[int]:
    beatmap = api_score.get('beatmap') or {}
    beatmap_id = beatmap.get('id') or api_score.get('beatmap_id')
    if beatmap_id is None:
        return None
    try:
        return int(beatmap_id)
    except (TypeError, ValueError):
        return None


def analyze_recent_play(beatmap: Beatmap, api_score: dict[str, Any], *, object_index: Optional[int] = None, replay_frames: Sequence[ReplayFrame] | None = None) -> AnalyzedScore:
    return analyze_api_score(beatmap=beatmap, api_score=api_score, object_index=object_index, replay_frames=replay_frames)


def analyze_choke(beatmap: Beatmap, api_score: dict[str, Any], *, object_index: Optional[int] = None, replay_frames: Sequence[ReplayFrame] | None = None) -> AnalyzedScore:
    return analyze_recent_play(beatmap=beatmap, api_score=api_score, object_index=object_index, replay_frames=replay_frames)


def analyze_fc_projection(beatmap: Beatmap, api_score: dict[str, Any], *, object_index: Optional[int] = None, replay_frames: Sequence[ReplayFrame] | None = None) -> AnalyzedScore:
    return analyze_recent_play(beatmap=beatmap, api_score=api_score, object_index=object_index, replay_frames=replay_frames)


def build_current_play_summary(analysis: AnalyzedScore, beatmap: Beatmap, api_score: dict[str, Any]) -> dict[str, Any]:
    score = analysis.score
    title = score.beatmap.title or beatmap.title
    version = score.beatmap.version or getattr(beatmap._inner, 'version', None) or ''
    artist = score.beatmap.artist or beatmap.artist
    username = score.username or score.user.username or 'Unknown user'
    score_value = int(score.score or 0)
    mods = format_mods(score.mods, score.mods_list)
    combo = score.max_combo or 0
    rank = score.rank or ('F' if not analysis.passed else '?')
    return {
        'player': username,
        'player_id': score.user_id,
        'title': title,
        'artist': artist,
        'version': version,
        'mods': mods,
        'rank': rank,
        'score': score_value,
        'legacy_score': score.legacy_score,
        'passed': analysis.passed,
        'accuracy': analysis.accuracy,
        'combo': combo,
        'current_pp': analysis.current_pp,
        'api_pp': score.pp,
        'if_fc_pp': analysis.if_fc_pp,
        'choke_pp': analysis.choke_pp,
        'completion': analysis.snapshot.progress * 100.0,
        'completion_text': analysis.map_completion_text,
        'partial_max_combo': analysis.partial_max_combo,
        'full_max_combo': analysis.full_max_combo,
        'statistics': analysis.score.statistics,
        'beatmap_id': score.beatmap_id,
        'beatmapset_id': score.beatmapset_id,
        'mode': score.mode,
        'created_at': score.created_at,
        'ended_at': score.ended_at,
        'replay_available': score.replay_available,
    }


def _resolve_beatmap_for_score(
    api_score: dict[str, Any],
    *,
    resolver: BeatmapResolver | None = None,
    beatmap_path: str | None = None,
    beatmap_content: str | None = None,
) -> Beatmap:
    beatmap_id = extract_beatmap_id(api_score)
    if beatmap_path or beatmap_content:
        return Beatmap(path=beatmap_path, content=beatmap_content)
    if resolver is None:
        raise MissingBeatmapError('Beatmap resolution requires a BeatmapResolver or local beatmap data.')
    if beatmap_id is None:
        raise MissingBeatmapError('API score did not contain a beatmap id.')
    return resolver.resolve(beatmap_id=beatmap_id)


def get_recent_analysis(
    client: Any,
    *,
    user_id: int | str,
    beatmap_path: str | None = None,
    beatmap_content: str | None = None,
    resolver: BeatmapResolver | None = None,
    mode: str = 'osu',
    include_fails: bool = True,
    object_index: Optional[int] = None,
) -> tuple[dict[str, Any], AnalyzedScore, Beatmap]:
    api_score = client.get_recent_score(user_id=user_id, mode=mode, include_fails=include_fails)
    if not api_score:
        raise ValueError('No recent score found for this user.')
    beatmap = _resolve_beatmap_for_score(api_score, resolver=resolver, beatmap_path=beatmap_path, beatmap_content=beatmap_content)
    analysis = analyze_recent_play(beatmap=beatmap, api_score=api_score, object_index=object_index)
    return api_score, analysis, beatmap


def get_recent_analysis_by_user(
    client: Any,
    *,
    user: int | str,
    resolver: BeatmapResolver,
    mode: str = 'osu',
    include_fails: bool = True,
    object_index: Optional[int] = None,
) -> tuple[dict[str, Any], AnalyzedScore, Beatmap]:
    return get_recent_analysis(client, user_id=user, resolver=resolver, mode=mode, include_fails=include_fails, object_index=object_index)


def get_best_play(client: Any, *, user: int | str, resolver: BeatmapResolver, mode: str = 'osu', object_index: Optional[int] = None) -> tuple[dict[str, Any], AnalyzedScore, Beatmap]:
    api_score = client.get_best_score(user_id=user, mode=mode)
    if not api_score:
        raise ValueError('No best score found for this user.')
    beatmap = _resolve_beatmap_for_score(api_score, resolver=resolver)
    analysis = analyze_recent_play(beatmap=beatmap, api_score=api_score, object_index=object_index)
    return api_score, analysis, beatmap
