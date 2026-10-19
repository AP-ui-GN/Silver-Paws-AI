"""Pose confidence summary.

A keypoint below the per-point threshold is already ignored inside each metric.
This module decides whether the pose result as a whole is trustworthy enough to
publish. A missing confidence is None, never zero.
"""

from __future__ import annotations

import math

import numpy as np


def summarize_keypoints(keypoints, *, frame_threshold: float) -> dict:
    """Return modelConfidence (0-1 or None), framesUsed, and framesTotal.

    A frame is counted in framesUsed when the mean confidence of its keypoints
    is at least ``frame_threshold``. framesTotal is every frame that was run.
    modelConfidence is the mean of finite keypoint confidences. It is None when
    no finite confidence was stored.
    """

    array = np.asarray(keypoints, dtype=np.float32)
    if array.ndim != 3 or array.shape[-1] < 3:
        raise ValueError("keypoints must have shape (frames, points, 3).")
    if not 0.0 <= frame_threshold <= 1.0:
        raise ValueError("frame_threshold must be between 0 and 1.")

    confidence = array[:, :, 2]
    frames_total = int(confidence.shape[0])
    finite = np.isfinite(confidence)
    if not np.any(finite):
        return {
            "modelConfidence": None,
            "framesUsed": 0,
            "framesTotal": frames_total,
        }

    frame_means: list[float] = []
    for frame in confidence:
        usable = frame[np.isfinite(frame)]
        if usable.size == 0:
            frame_means.append(0.0)
            continue
        frame_means.append(float(np.mean(usable)))

    frames_used = sum(1 for value in frame_means if value >= frame_threshold)
    mean = float(np.mean(confidence[finite]))
    if not math.isfinite(mean):
        model_confidence = None
    else:
        model_confidence = round(max(0.0, min(1.0, mean)), 4)

    return {
        "modelConfidence": model_confidence,
        "framesUsed": frames_used,
        "framesTotal": frames_total,
    }


def pose_is_trusted(summary: dict, *, minimum: float) -> bool:
    """True when the pose mean is high enough and at least one frame was used."""

    confidence = summary.get("modelConfidence")
    frames_used = summary.get("framesUsed")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return False
    if not isinstance(frames_used, int) or isinstance(frames_used, bool):
        return False
    return confidence >= minimum and frames_used > 0
