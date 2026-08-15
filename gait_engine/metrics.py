"""Small, explainable gait metrics for the first MoveNet validation pass."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

LEFT_ANKLE_INDEX = 15
RIGHT_ANKLE_INDEX = 16


@dataclass(frozen=True)
class GaitMetrics:
    """Summary values returned by the initial validation metric."""

    frame_count: int
    valid_left_ankle_frames: int
    valid_right_ankle_frames: int
    mean_keypoint_confidence: float
    left_ankle_motion: float
    right_ankle_motion: float
    stride_symmetry_score: float | None
    asymmetry_percent: float | None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable metric values."""

        return asdict(self)


def _motion_energy(vertical_positions: np.ndarray) -> tuple[float, int]:
    """Return total frame-to-frame vertical movement and valid frame count."""

    valid = np.isfinite(vertical_positions)
    valid_count = int(np.count_nonzero(valid))
    if valid_count < 2:
        return 0.0, valid_count

    # Only compare adjacent observations that are both confidently detected.
    adjacent_valid = valid[:-1] & valid[1:]
    if not np.any(adjacent_valid):
        return 0.0, valid_count

    movement = np.abs(np.diff(vertical_positions))
    return float(np.sum(movement[adjacent_valid])), valid_count


def compute_gait_metrics(
    keypoints: np.ndarray,
    *,
    confidence_threshold: float = 0.2,
) -> GaitMetrics:
    """Compute a basic left/right ankle motion symmetry metric.

    ``keypoints`` must be shaped ``(frames, 17, 3)`` with MoveNet's
    ``(y, x, confidence)`` order. The score is 1.0 when both sides have equal
    vertical motion and approaches 0.0 as their motion diverges:

        1 - abs(left_motion - right_motion) / (left_motion + right_motion)

    This is an engineering validation metric, not a clinical diagnosis. It
    assumes the model's left/right ankle detections are meaningful.
    """

    keypoints = np.asarray(keypoints, dtype=np.float32)
    if keypoints.ndim != 3 or keypoints.shape[1:] != (17, 3):
        raise ValueError(
            "keypoints must have shape (frames, 17, 3); "
            f"received {keypoints.shape}."
        )
    if keypoints.shape[0] == 0:
        raise ValueError("At least one frame is required.")
    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be between 0 and 1.")

    confidence = keypoints[:, :, 2]
    usable_confidence = confidence[np.isfinite(confidence)]
    mean_confidence = (
        float(np.mean(usable_confidence)) if usable_confidence.size else 0.0
    )

    left_y = keypoints[:, LEFT_ANKLE_INDEX, 0].copy()
    right_y = keypoints[:, RIGHT_ANKLE_INDEX, 0].copy()
    left_y[confidence[:, LEFT_ANKLE_INDEX] < confidence_threshold] = np.nan
    right_y[confidence[:, RIGHT_ANKLE_INDEX] < confidence_threshold] = np.nan

    left_motion, valid_left = _motion_energy(left_y)
    right_motion, valid_right = _motion_energy(right_y)
    total_motion = left_motion + right_motion
    if valid_left < 2 or valid_right < 2 or total_motion == 0.0:
        # A missing/standing pose is not evidence of perfect symmetry. Return
        # null so the later API can distinguish "not enough signal" from 1.0.
        symmetry_score = None
        asymmetry_percent = None
    else:
        symmetry_score = 1.0 - abs(left_motion - right_motion) / total_motion
        symmetry_score = float(np.clip(symmetry_score, 0.0, 1.0))
        asymmetry_percent = round((1.0 - symmetry_score) * 100.0, 3)

    return GaitMetrics(
        frame_count=int(keypoints.shape[0]),
        valid_left_ankle_frames=valid_left,
        valid_right_ankle_frames=valid_right,
        mean_keypoint_confidence=round(mean_confidence, 6),
        left_ankle_motion=round(left_motion, 6),
        right_ankle_motion=round(right_motion, 6),
        stride_symmetry_score=(
            None if symmetry_score is None else round(symmetry_score, 6)
        ),
        asymmetry_percent=asymmetry_percent,
    )
