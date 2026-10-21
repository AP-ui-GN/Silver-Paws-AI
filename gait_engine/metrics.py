"""Left/right hind-paw motion from quadruped pose landmarks.

The field names say "ankle" because that is the measurement the rest of the
app already stores. The landmarks are the hind paws, AP-10K ``L_B_Paw`` and
``R_B_Paw``. A side with fewer than two confident frames is None, not zero.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .quadpose import LEFT_HIND_PAW_INDEX, RIGHT_HIND_PAW_INDEX

LEFT_ANKLE_INDEX = LEFT_HIND_PAW_INDEX
RIGHT_ANKLE_INDEX = RIGHT_HIND_PAW_INDEX


@dataclass(frozen=True)
class GaitMetrics:
    """Summary values returned by the initial validation metric."""

    frame_count: int
    valid_left_ankle_frames: int
    valid_right_ankle_frames: int
    mean_keypoint_confidence: float
    left_ankle_motion: float | None
    right_ankle_motion: float | None
    stride_symmetry_score: float | None
    asymmetry_percent: float | None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable metric values."""

        return asdict(self)


def _motion_energy(vertical_positions: np.ndarray) -> tuple[float | None, int]:
    """Return total frame-to-frame vertical movement and valid frame count.

    None means that side was not measured. A measured animal that does not
    move returns 0.
    """

    valid = np.isfinite(vertical_positions)
    valid_count = int(np.count_nonzero(valid))
    if valid_count < 2:
        return None, valid_count

    # Only compare adjacent observations that are both confidently detected.
    adjacent_valid = valid[:-1] & valid[1:]
    if not np.any(adjacent_valid):
        return None, valid_count

    movement = np.abs(np.diff(vertical_positions))
    return float(np.sum(movement[adjacent_valid])), valid_count


def compute_gait_metrics(
    keypoints: np.ndarray,
    *,
    confidence_threshold: float = 0.2,
) -> GaitMetrics:
    """Compute a basic left/right ankle motion symmetry metric.

    ``keypoints`` must be shaped ``(frames, 17, 3)`` in
    ``(y, x, confidence)`` order. Indexes 13 and 16 are the left and right
    hind paws. The score is 1.0 when both sides have equal vertical motion
    and approaches 0.0 as their motion diverges:

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
    if (
        left_motion is None
        or right_motion is None
        or valid_left < 2
        or valid_right < 2
        or left_motion + right_motion == 0.0
    ):
        # A missing side, or a standing pose, is not evidence of perfect
        # symmetry. None is distinct from a score of 1.0.
        symmetry_score = None
        asymmetry_percent = None
    else:
        symmetry_score = 1.0 - abs(left_motion - right_motion) / (left_motion + right_motion)
        symmetry_score = float(np.clip(symmetry_score, 0.0, 1.0))
        asymmetry_percent = round((1.0 - symmetry_score) * 100.0, 3)

    return GaitMetrics(
        frame_count=int(keypoints.shape[0]),
        valid_left_ankle_frames=valid_left,
        valid_right_ankle_frames=valid_right,
        mean_keypoint_confidence=round(mean_confidence, 6),
        left_ankle_motion=None if left_motion is None else round(left_motion, 6),
        right_ankle_motion=None if right_motion is None else round(right_motion, 6),
        stride_symmetry_score=(
            None if symmetry_score is None else round(symmetry_score, 6)
        ),
        asymmetry_percent=asymmetry_percent,
    )
