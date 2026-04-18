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

import lzma
import struct

from osukit import (
    parse_replay_frame_string,
    parse_osr_bytes,
    ReplayData,
    ProfileResult,
)


def _enc_string(value: str) -> bytes:
    if value == '':
        return b'\x00'
    data = value.encode('utf-8')
    out = bytearray([0x0B])
    n = len(data)
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    out.extend(data)
    return bytes(out)


def build_osr_blob() -> bytes:
    replay_text = '1000|256|192|5,500|300|192|1,-12345|0|0|0,'
    compressed = lzma.compress(replay_text.encode('utf-8'))
    parts = [
        struct.pack('<B', 0),
        struct.pack('<I', 20250101),
        _enc_string('beatmap-md5'),
        _enc_string('Pedro'),
        _enc_string('replay-md5'),
        struct.pack('<H', 300),
        struct.pack('<H', 100),
        struct.pack('<H', 50),
        struct.pack('<H', 20),
        struct.pack('<H', 10),
        struct.pack('<H', 3),
        struct.pack('<I', 1234567),
        struct.pack('<H', 456),
        struct.pack('<B', 1),
        struct.pack('<I', 72),
        _enc_string('0|100,1000|50,'),
        struct.pack('<q', 638000000000000000),
        struct.pack('<I', len(compressed)),
        compressed,
        struct.pack('<q', 987654321),
    ]
    return b''.join(parts)


def test_parse_replay_frame_string():
    frames = parse_replay_frame_string('16|10|20|1,32|30|40|5,-12345|0|0|0,')
    assert len(frames) == 2
    assert frames[1].time_ms == 48
    assert frames[1].keys == 5


def test_parse_osr_bytes_roundtrip():
    data = parse_osr_bytes(build_osr_blob())
    assert isinstance(data, ReplayData)
    assert data.username == 'Pedro'
    assert data.score == 1234567
    assert data.mods == 72
    assert len(data.frames) == 2
    assert data.frames[-1].time_ms == 1500
    assert data.score_id == 987654321


def test_profile_result_has_url():
    profile = ProfileResult.from_api_v2({'id': 123, 'username': 'Pedro', 'statistics': {}})
    payload = profile.to_embed_payload()
    assert payload['url'].endswith('/123')
