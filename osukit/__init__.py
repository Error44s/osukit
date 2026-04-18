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

# Core beatmap / mods
from .api import Beatmap, Difficulty, Performance, GameMode
from .beatmap import Mods
from .difficulty import DifficultyAttributes
from .performance import PerformanceAttributes
from .taiko_difficulty import TaikoDifficultyAttributes
from .taiko_performance import TaikoPerformanceAttributes

# Models
from .models import (
    ScoreStatistics, BeatmapRef, UserRef,
    ScoreState, PartialPlaySnapshot, ProjectedScore,
    AnalyzedScore, PaceMetrics,
)

# Live projections
from .live import (
    build_partial_snapshot,
    estimate_failed_score,
    project_score,
    estimate_object_index_from_statistics,
    analyze_score_state,
    analyze_api_score,
)

# API client + OAuth
from .client import OsuApiClient, OsuApiError, TokenError, OAuthToken, OsuOAuthClient

# Beatmap resolution
from .resolver import BeatmapResolver

# Errors
from .errors import (
    RosuError, BeatmapResolveError, MissingBeatmapError,
    UnsupportedModeError, ScoreAnalysisError, RateLimitError,
)

# Utilities
from .cache import TTLCache

# Result types
from .results import ProfileResult, PlayResult, PlayListResult, CompareResult, MapResult

# High-level bot client
from .bot_client import OsuBotClient, BotClientConfig

# Bot helpers
from .bot import (
    analyze_recent_play,
    analyze_choke,
    analyze_fc_projection,
    get_recent_analysis,
    get_recent_analysis_by_user,
    get_best_play,
    build_current_play_summary,
    format_analysis_markdown,
    build_embed_payload,
    format_mods,
    parse_mods,
    mods_to_int,
)

# Judgement reconstruction (osu!standard deep + non-std preview)
from .judgement import (
    JudgedObject,
    JudgementReconstruction,
    SliderTickResult,       # NEW v1.9 per-tick hit tracking
    SpinnerResult,          # NEW v1.9 spinner completion/bonus
    reconstruct_judgements,
)

# Replay parsing
from .replay import (
    ReplayFrame, ReplayCursor, ReplayData,
    infer_object_index_from_time,
    infer_object_index_from_replay_frames,
    parse_replay_frame_string,
    parse_osr_bytes,
    parse_osr_file,
)

# Advantage layer: coaching / skill / choke insights
from .insights import (
    SkillProfile,
    ChokeInfo,
    Recommendation,
    SessionInsight,
    classify_choke,
    analyze_skill_profile,
    recommend_training_focus,
    summarize_recent_fails,
    build_session_insight,
)

# Benchmark / golden test tooling
from .benchmark import (
    DifficultyExpectation,
    PerformanceExpectation,
    GoldenScoreCase,
    MetricComparison,
    FocusRecommendation,
    BenchmarkResult,
    BenchmarkSuiteReport,
    ReportDelta,
    ReferenceImportSummary,
    CandidateComparison,
    CandidateMatrixReport,
    run_golden_case,
    run_golden_suite,
    save_golden_cases,
    load_golden_cases,
    create_golden_case,
    infer_case_tags,
    compare_benchmark_reports,
    load_reference_cases,
    run_candidate_matrix,
)

# Catch local engine [NEW v1.9]
from .catch_engine import (
    CatchDifficultyAttributes,
    CatchPerformanceAttributes,
    calculate_catch_difficulty,
    calculate_catch_performance,
    project_catch_score,
)

# Mania local engine [NEW v1.9]
from .mania_engine import (
    ManiaDifficultyAttributes,
    ManiaPerformanceAttributes,
    calculate_mania_difficulty,
    calculate_mania_performance,
    project_mania_score,
)

__version__ = '2.5.0'

__all__ = [
    # Core
    'Beatmap', 'Difficulty', 'Performance', 'GameMode',
    'Mods',
    'DifficultyAttributes', 'PerformanceAttributes',
    'TaikoDifficultyAttributes', 'TaikoPerformanceAttributes',
    # Models
    'ScoreStatistics', 'BeatmapRef', 'UserRef', 'ScoreState',
    'PartialPlaySnapshot', 'ProjectedScore', 'AnalyzedScore', 'PaceMetrics',
    # Live
    'build_partial_snapshot', 'estimate_failed_score', 'project_score',
    'estimate_object_index_from_statistics', 'analyze_score_state', 'analyze_api_score',
    # Client
    'OsuApiClient', 'OsuApiError', 'TokenError', 'OAuthToken', 'OsuOAuthClient',
    # Resolver
    'BeatmapResolver',
    # Errors
    'RosuError', 'BeatmapResolveError', 'MissingBeatmapError',
    'UnsupportedModeError', 'ScoreAnalysisError', 'RateLimitError',
    # Utils
    'TTLCache',
    # Results
    'ProfileResult', 'PlayResult', 'PlayListResult', 'CompareResult', 'MapResult',
    # Bot client
    'OsuBotClient', 'BotClientConfig',
    # Bot helpers
    'analyze_recent_play', 'analyze_choke', 'analyze_fc_projection',
    'get_recent_analysis', 'get_recent_analysis_by_user', 'get_best_play',
    'build_current_play_summary', 'format_analysis_markdown', 'build_embed_payload',
    'format_mods', 'parse_mods', 'mods_to_int',
    # Judgement
    'JudgedObject', 'JudgementReconstruction',
    'SliderTickResult', 'SpinnerResult',
    'reconstruct_judgements',
    # Replay
    'ReplayFrame', 'ReplayCursor', 'ReplayData',
    'infer_object_index_from_time', 'infer_object_index_from_replay_frames',
    'parse_replay_frame_string', 'parse_osr_bytes', 'parse_osr_file',
    # Insights
    'SkillProfile', 'ChokeInfo', 'Recommendation', 'SessionInsight',
    'classify_choke', 'analyze_skill_profile', 'recommend_training_focus',
    'summarize_recent_fails', 'build_session_insight',
    # Benchmarking
    'DifficultyExpectation', 'PerformanceExpectation', 'GoldenScoreCase',
    'MetricComparison', 'FocusRecommendation', 'BenchmarkResult', 'BenchmarkSuiteReport', 'ReportDelta',
    'ReferenceImportSummary', 'CandidateComparison', 'CandidateMatrixReport',
    'run_golden_case', 'run_golden_suite', 'save_golden_cases',
    'load_golden_cases', 'create_golden_case', 'infer_case_tags', 'compare_benchmark_reports',
    'load_reference_cases', 'run_candidate_matrix',
    # Catch engine
    'CatchDifficultyAttributes', 'CatchPerformanceAttributes',
    'calculate_catch_difficulty', 'calculate_catch_performance', 'project_catch_score',
    # Mania engine
    'ManiaDifficultyAttributes', 'ManiaPerformanceAttributes',
    'calculate_mania_difficulty', 'calculate_mania_performance', 'project_mania_score',
    # Tuning
    'DEFAULT_STD_TUNING', 'StdTuningProfile', 'CalibrationObjective', 'CalibrationOutcome', 'CalibrationPreset',
    'build_calibration_preset', 'optimize_standard_tuning', 'optimize_with_preset', 'build_candidate_profiles',
]

from .tuning import DEFAULT_STD_TUNING, StdTuningProfile, CalibrationObjective, CalibrationOutcome, CalibrationPreset, build_calibration_preset, optimize_standard_tuning, optimize_with_preset, build_candidate_profiles
