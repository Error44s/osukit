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


class RosuError(Exception):
    """Base exception for osukit."""


class OsuApiError(RosuError):
    """Raised when the osu! API returns an error or unexpected response."""


class TokenError(OsuApiError):
    """Raised when OAuth token handling fails."""


class BeatmapResolveError(RosuError):
    """Raised when a beatmap cannot be downloaded or resolved."""


class MissingBeatmapError(BeatmapResolveError):
    """Raised when beatmap input is required but missing."""


class UnsupportedModeError(RosuError):
    """Raised when a game mode is not supported by a specific local calculator path."""


class ScoreAnalysisError(RosuError):
    """Raised when local score analysis or projections fail."""


class RateLimitError(OsuApiError):
    """Raised when the osu! API rate limits a request."""

    def __init__(self, message: str, *, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after
