"""Standalone gait-analysis building blocks for SilverPaws AI."""

from .features import hip_stability, motion_statistics, movement_consistency
from .metrics import GaitMetrics, compute_gait_metrics
from .motion import MotionSignal, read_motion_signal
from .quadruped import (
    KEYPOINT_NAMES,
    MODEL_NAME,
    MODEL_VERSION,
    PIPELINE_ID,
    extract_keypoints_from_video,
    load_quadruped,
)
from .pipeline import analyze_clip
from .wellness import DEFAULT_WEIGHTS, overall_score, score_factors

__all__ = [
    "DEFAULT_WEIGHTS",
    "GaitMetrics",
    "KEYPOINT_NAMES",
    "MODEL_NAME",
    "MODEL_VERSION",
    "MotionSignal",
    "PIPELINE_ID",
    "analyze_clip",
    "compute_gait_metrics",
    "extract_keypoints_from_video",
    "hip_stability",
    "load_quadruped",
    "motion_statistics",
    "movement_consistency",
    "overall_score",
    "read_motion_signal",
    "score_factors",
]
