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

import lzma
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from .api import Beatmap
from .beatmap import Beatmap as CoreBeatmap


@dataclass
class ReplayFrame:
    time_ms: float
    x: float = 0.0
    y: float = 0.0
    keys: int = 0


@dataclass
class ReplayCursor:
    object_index: int
    object_time_ms: float
    frame_time_ms: float
    progress: float


@dataclass
class ReplayData:
    mode: int
    version: int
    beatmap_md5: str
    username: str
    replay_md5: str
    count_300: int
    count_100: int
    count_50: int
    count_geki: int
    count_katu: int
    count_miss: int
    score: int
    max_combo: int
    perfect_combo: bool
    mods: int
    life_bar_graph: str
    timestamp_windows_ticks: int
    frames: list[ReplayFrame] = field(default_factory=list)
    score_id: int | None = None
    raw_replay_data: str = ''

    @property
    def duration_ms(self) -> float:
        return self.frames[-1].time_ms if self.frames else 0.0

    @property
    def final_keys(self) -> int:
        return self.frames[-1].keys if self.frames else 0


def _normalise_beatmap(beatmap: Beatmap | CoreBeatmap) -> CoreBeatmap:
    return beatmap._inner if isinstance(beatmap, Beatmap) else beatmap


def infer_object_index_from_time(beatmap: Beatmap | CoreBeatmap, time_ms: float) -> int:
    bm = _normalise_beatmap(beatmap)
    if not bm.hit_objects:
        return 0
    idx = 0
    for i, obj in enumerate(bm.hit_objects, start=1):
        end_time = getattr(obj, 'end_time', getattr(obj, 'time', 0.0))
        if end_time <= time_ms:
            idx = i
        else:
            break
    return idx


def infer_object_index_from_replay_frames(beatmap: Beatmap | CoreBeatmap, frames: Sequence[ReplayFrame] | Iterable[ReplayFrame]) -> ReplayCursor:
    bm = _normalise_beatmap(beatmap)
    frames = list(frames)
    if not frames:
        return ReplayCursor(object_index=0, object_time_ms=0.0, frame_time_ms=0.0, progress=0.0)
    last = max(frames, key=lambda f: f.time_ms)
    idx = infer_object_index_from_time(bm, last.time_ms)
    object_time = 0.0
    if idx > 0 and idx <= len(bm.hit_objects):
        object_time = float(getattr(bm.hit_objects[idx - 1], 'time', 0.0))
    progress = (idx / len(bm.hit_objects)) if bm.hit_objects else 0.0
    return ReplayCursor(object_index=idx, object_time_ms=object_time, frame_time_ms=float(last.time_ms), progress=progress)


def parse_replay_frame_string(data: str) -> list[ReplayFrame]:
    frames: list[ReplayFrame] = []
    if not data:
        return frames
    current_time = 0
    for part in data.split(','):
        if not part:
            continue
        bits = part.split('|')
        if len(bits) < 4:
            continue
        try:
            delta = int(float(bits[0]))
            if delta == -12345:
                break
            current_time += delta
            frames.append(
                ReplayFrame(
                    time_ms=float(current_time),
                    x=float(bits[1]),
                    y=float(bits[2]),
                    keys=int(float(bits[3])),
                )
            )
        except (TypeError, ValueError):
            continue
    return frames


def _read_byte(blob: bytes, offset: int) -> tuple[int, int]:
    return blob[offset], offset + 1


def _read_bool(blob: bytes, offset: int) -> tuple[bool, int]:
    value, offset = _read_byte(blob, offset)
    return bool(value), offset


def _read_short(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from('<H', blob, offset)[0], offset + 2


def _read_int(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from('<I', blob, offset)[0], offset + 4


def _read_long(blob: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from('<q', blob, offset)[0], offset + 8


def _read_uleb128(blob: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        byte = blob[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, offset


def _read_string(blob: bytes, offset: int) -> tuple[str, int]:
    marker, offset = _read_byte(blob, offset)
    if marker == 0x00:
        return '', offset
    if marker != 0x0B:
        raise ValueError('Invalid replay string marker.')
    length, offset = _read_uleb128(blob, offset)
    value = blob[offset: offset + length].decode('utf-8', errors='replace')
    return value, offset + length


def parse_osr_bytes(blob: bytes) -> ReplayData:
    offset = 0
    mode, offset = _read_byte(blob, offset)
    version, offset = _read_int(blob, offset)
    beatmap_md5, offset = _read_string(blob, offset)
    username, offset = _read_string(blob, offset)
    replay_md5, offset = _read_string(blob, offset)
    count_300, offset = _read_short(blob, offset)
    count_100, offset = _read_short(blob, offset)
    count_50, offset = _read_short(blob, offset)
    count_geki, offset = _read_short(blob, offset)
    count_katu, offset = _read_short(blob, offset)
    count_miss, offset = _read_short(blob, offset)
    score, offset = _read_int(blob, offset)
    max_combo, offset = _read_short(blob, offset)
    perfect_combo, offset = _read_bool(blob, offset)
    mods, offset = _read_int(blob, offset)
    life_bar_graph, offset = _read_string(blob, offset)
    timestamp_windows_ticks, offset = _read_long(blob, offset)
    replay_length, offset = _read_int(blob, offset)
    replay_payload = blob[offset: offset + replay_length]
    offset += replay_length
    replay_data = lzma.decompress(replay_payload).decode('utf-8', errors='replace') if replay_length > 0 else ''
    score_id = None
    if len(blob) - offset >= 8:
        score_id, offset = _read_long(blob, offset)
    frames = parse_replay_frame_string(replay_data)
    return ReplayData(
        mode=mode,
        version=version,
        beatmap_md5=beatmap_md5,
        username=username,
        replay_md5=replay_md5,
        count_300=count_300,
        count_100=count_100,
        count_50=count_50,
        count_geki=count_geki,
        count_katu=count_katu,
        count_miss=count_miss,
        score=score,
        max_combo=max_combo,
        perfect_combo=perfect_combo,
        mods=mods,
        life_bar_graph=life_bar_graph,
        timestamp_windows_ticks=timestamp_windows_ticks,
        frames=frames,
        score_id=score_id,
        raw_replay_data=replay_data,
    )


def parse_osr_file(path: str | Path) -> ReplayData:
    return parse_osr_bytes(Path(path).read_bytes())
