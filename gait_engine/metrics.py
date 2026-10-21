"""Paw motion from AP-10K keypoints.

Stride symmetry uses the model's left and right back paws (``L_B_Paw`` and
``R_B_Paw``). Fore-paw motion uses ``L_F_Paw`` and ``R_F_Paw``. Those are
the paw keypoints RTMPose-m actually outputs. This is not a clinical score.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .quadruped import (
    KEYPOINT_NAMES,
    L_FORE_PAW_INDEX,
    L_HIND_PAW_INDEX,
    R_FORE_PAW_INDEX,
    R_HIND_PAW_INDEX,
)


@dataclass(frozen=True)
class PairMotion:
    """Vertical motion for one left/right keypoint pair."""

    valid_left_frames: int
    valid_right_frames: int
    left_motion: float
    right_motion: float
    symmetry_score: float | None
    asymmetry_percent: float | None


@dataclass(frozen=True)
class GaitMetrics:
    """Hind-paw stride plus the fore-paw motion the model also outputs."""

    frame_count: int
    mean_keypoint_confidence: float
    hind: PairMotion
    fore: PairMotion


def _motion_energy(vertical_positions: np.ndarray) -> tuple[float, int]:
    """Return total frame-to-frame vertical movement and valid frame count."""

    valid = np.isfinite(vertical_positions)
    valid_count = int(np.count_nonzero(valid))
    if valid_count < 2:
        return 0.0, valid_count

    adjacent_valid = valid[:-1] & valid[1:]
    if not np.any(adjacent_valid):
        return 0.0, valid_count

    movement = np.abs(np.diff(vertical_positions))
    return float(np.sum(movement[adjacent_valid])), valid_count


def pair_motion(
    keypoints: np.ndarray,
    left_index: int,
    right_index: int,
    *,
    confidence_threshold: float = 0.2,
) -> PairMotion:
    """Compare vertical motion of two keypoints the caller names.

    The score is 1.0 when both sides have equal vertical motion:

        1 - abs(left - right) / (left + right)

    Too little confident motion returns a null score, not 1.0.
    """

    keypoints = np.asarray(keypoints, dtype=np.float32)
    if keypoints.ndim != 3 or keypoints.shape[1:] != (len(KEYPOINT_NAMES), 3):
        raise ValueError(
            "keypoints must have shape "
            f"(frames, {len(KEYPOINT_NAMES)}, 3); received {keypoints.shape}."
        )
    if keypoints.shape[0] == 0:
        raise ValueError("At least one frame is required.")
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0 and 1.")

    confidence = keypoints[:, :, 2]
    left_y = keypoints[:, left_index, 0].copy()
    right_y = keypoints[:, right_index, 0].copy()
    left_y[confidence[:, left_index] < confidence_threshold] = np.nan
    right_y[confidence[:, right_index] < confidence_threshold] = np.nan

    left_energy, valid_left = _motion_energy(left_y)
    right_energy, valid_right = _motion_energy(right_y)
    total = left_energy + right_energy
    if valid_left < 2 or valid_right < 2 or total == 0.0:
        symmetry = None
        asymmetry = None
    else:
        symmetry = float(np.clip(1.0 - abs(left_energy - right_energy) / total, 0.0, 1.0))
        asymmetry = round((1.0 - symmetry) * 100.0, 3)

    return PairMotion(
        valid_left_frames=valid_left,
        valid_right_frames=valid_right,
        left_motion=round(left_energy, 6),
        right_motion=round(right_energy, 6),
        symmetry_score=None if symmetry is None else round(symmetry, 6),
        asymmetry_percent=asymmetry,
    )


def compute_gait_metrics(
    keypoints: np.ndarray,
    *,
    confidence_threshold: float = 0.2,
) -> GaitMetrics:
    """Measure hind-paw stride and fore-paw motion from AP-10K keypoints."""

    keypoints = np.asarray(keypoints, dtype=np.float32)
    confidence = keypoints[:, :, 2]
    usable = confidence[np.isfinite(confidence)]
    mean_confidence = float(np.mean(usable)) if usable.size else 0.0

    return GaitMetrics(
        frame_count=int(keypoints.shape[0]),
        mean_keypoint_confidence=round(mean_confidence, 6),
        hind=pair_motion(
            keypoints,
            L_HIND_PAW_INDEX,
            R_HIND_PAW_INDEX,
            confidence_threshold=confidence_threshold,
        ),
        fore=pair_motion(
            keypoints,
            L_FORE_PAW_INDEX,
            R_FORE_PAW_INDEX,
            confidence_threshold=confidence_threshold,
        ),
    )
