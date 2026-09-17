"""End-to-end clip analysis.

    video -> frames -> (pose landmarks | picture motion) -> measurements
          -> factor scores -> overall indicator -> plain-language observation

Two pipelines are supported and the best available one is chosen per clip:

* ``movenet``       pose landmarks, so left/right stride symmetry can be measured.
* ``opencv-motion`` frame-to-frame picture change only. Used whenever TensorFlow
                    or the pose model is unavailable, which keeps the product
                    usable on a machine with just OpenCV installed.

The returned dictionary matches the ``AnalyzeResult`` schema in
`lib/api-spec/openapi.yaml`, so the API server can validate it before replying.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .features import MOTION_FLOOR, hip_stability, motion_statistics
from .metrics import compute_gait_metrics
from .motion import read_motion_signal
from .wellness import (
    DEFAULT_WEIGHTS,
    build_limitations,
    build_observation,
    concerning_change,
    historical_change_factor,
    overall_score,
    score_factors,
    weights_used,
)

# Long clips are truncated. The motion pipeline is cheap, pose inference is not.
MAX_MOTION_FRAMES = 900
MAX_POSE_FRAMES = 120

POSE_CONFIDENCE_THRESHOLD = 0.2

# Pose detections below this mean confidence are reported but not trusted enough
# to score left/right symmetry from.
MIN_POSE_CONFIDENCE = 0.3
MIN_ANKLE_FRAMES = 10

MIN_COMPARABLE_FRAMES = 5


def _clean_pet_name(pet_name: str | None) -> str | None:
    """Keep the display name short and free of line breaks before it enters text."""

    if not pet_name:
        return None
    cleaned = " ".join(pet_name.split())[:40]
    return cleaned or None


def _try_pose(
    video_path: Path,
    *,
    model_url: str | None,
    max_frames: int,
) -> tuple[Any | None, str | None]:
    """Try to extract pose landmarks. Returns (keypoints, skip_reason)."""

    try:
        from .movenet import DEFAULT_MODEL_URL, extract_keypoints_from_video, load_movenet
    except ImportError as exc:
        return None, f"pose modules unavailable: {exc}"

    try:
        model = load_movenet(model_url or DEFAULT_MODEL_URL)
        keypoints, _fps = extract_keypoints_from_video(
            video_path,
            model,
            min_confidence=POSE_CONFIDENCE_THRESHOLD,
            max_frames=max_frames,
        )
    except Exception as exc:  # noqa: BLE001 - any pose failure must fall back
        # Missing TensorFlow, no network for the model download, an unreadable
        # frame: none of these should fail the request, because the motion
        # pipeline can still measure the clip.
        return None, f"{type(exc).__name__}: {exc}"

    return keypoints, None


def _assess_signal(pipeline: str, measurements: dict) -> tuple[str, str]:
    """Decide how much the measurements from this clip can be trusted."""

    if measurements["frameCount"] < MIN_COMPARABLE_FRAMES:
        return (
            "unusable",
            "The clip was too short to compare enough frames.",
        )

    if measurements["motionMean"] < MOTION_FLOOR:
        return (
            "unusable",
            "Almost no movement was visible between frames, so there was nothing to measure.",
        )

    if pipeline == "opencv-motion":
        return (
            "limited",
            "No pet pose landmarks were available for this clip, so the left and right "
            "sides were not compared.",
        )

    if not measurements["symmetryReliable"]:
        return (
            "limited",
            "Pose landmarks were found, but the leg detections were not confident enough "
            "to compare the two sides.",
        )

    return (
        "good",
        "Pose landmarks were confident enough to compare both sides of the body.",
    )


def analyze_clip(
    video_path: str | Path,
    *,
    pet_name: str | None = None,
    previous_overall: float | None = None,
    previous_pipeline: str | None = None,
    use_pose: bool = True,
    model_url: str | None = None,
) -> dict[str, Any]:
    """Analyze one movement clip and return an ``AnalyzeResult`` dictionary.

    Raises:
        FileNotFoundError: the clip does not exist.
        ValueError: the clip could not be decoded as video.
    """

    path = Path(video_path)
    signal = read_motion_signal(path, max_frames=MAX_MOTION_FRAMES)
    motion_mean, motion_std, motion_coverage = motion_statistics(signal.frame_motion)

    measurements: dict[str, Any] = {
        "frameCount": signal.frames_read,
        "durationSeconds": signal.duration_seconds,
        "meanKeypointConfidence": None,
        "leftAnkleMotion": None,
        "rightAnkleMotion": None,
        "strideSymmetry": None,
        "asymmetryPercent": None,
        "motionMean": motion_mean,
        "motionStd": motion_std,
        "motionCoverage": motion_coverage,
        "hipStability": None,
        "symmetryReliable": False,
    }

    pipeline = "opencv-motion"
    pose_skip_reason: str | None = "pose extraction was disabled for this run"

    if use_pose:
        keypoints, pose_skip_reason = _try_pose(
            path,
            model_url=model_url,
            max_frames=MAX_POSE_FRAMES,
        )
        if keypoints is not None:
            pipeline = "movenet"
            gait = compute_gait_metrics(
                keypoints,
                confidence_threshold=POSE_CONFIDENCE_THRESHOLD,
            )
            measurements["meanKeypointConfidence"] = gait.mean_keypoint_confidence
            measurements["leftAnkleMotion"] = gait.left_ankle_motion
            measurements["rightAnkleMotion"] = gait.right_ankle_motion
            measurements["strideSymmetry"] = gait.stride_symmetry_score
            measurements["asymmetryPercent"] = gait.asymmetry_percent
            measurements["hipStability"] = hip_stability(
                keypoints,
                confidence_threshold=POSE_CONFIDENCE_THRESHOLD,
            )
            measurements["symmetryReliable"] = bool(
                gait.stride_symmetry_score is not None
                and gait.mean_keypoint_confidence >= MIN_POSE_CONFIDENCE
                and gait.valid_left_ankle_frames >= MIN_ANKLE_FRAMES
                and gait.valid_right_ankle_frames >= MIN_ANKLE_FRAMES
            )

    signal_quality, signal_note = _assess_signal(pipeline, measurements)

    if signal_quality == "unusable":
        # Refuse to publish scores that were built from nothing.
        factors: dict[str, float | None] = {
            "movementConsistency": None,
            "symmetry": None,
            "mobility": None,
            "activity": None,
            "historicalChange": None,
        }
        overall = None
    else:
        factors = score_factors(measurements)
        overall = overall_score(factors)

    # Trends are only meaningful between clips measured the same way.
    comparable_previous = (
        previous_overall
        if previous_overall is not None and previous_pipeline == pipeline
        else None
    )

    # Sudarshan owns this factor. Once it returns a score AND a weight is added
    # to DEFAULT_WEIGHTS, the overall indicator is recomputed so the new factor
    # actually counts.
    if signal_quality != "unusable":
        factors["historicalChange"] = historical_change_factor(
            overall, comparable_previous
        )
        if "historicalChange" in DEFAULT_WEIGHTS:
            overall = overall_score(factors)

    concerning = concerning_change(overall, comparable_previous, measurements)
    observation = build_observation(
        pet_name=_clean_pet_name(pet_name),
        measurements=measurements,
        factors=factors,
        overall=overall,
        previous_overall=comparable_previous,
        signal_quality=signal_quality,
        signal_note=signal_note,
        concerning=concerning,
    )

    confidence = measurements["meanKeypointConfidence"]

    return {
        "ok": True,
        "pipeline": pipeline,
        "signalQuality": signal_quality,
        "signalNote": signal_note,
        "measurements": measurements,
        "factors": factors,
        "overallScore": overall,
        "strideSymmetryScore": factors["symmetry"],
        "asymmetryPercent": (
            measurements["asymmetryPercent"] if measurements["symmetryReliable"] else None
        ),
        "confidence": None if confidence is None else round(confidence * 100, 1),
        "observation": observation,
        "limitations": build_limitations(pipeline, signal_quality),
        "concerningChange": concerning,
        "usedLlm": False,
        "weightsUsed": weights_used(factors),
        "diagnostics": {
            "fps": signal.fps,
            "framePairs": len(signal.frame_motion),
            "poseSkipReason": pose_skip_reason,
            "configuredWeights": DEFAULT_WEIGHTS,
            "comparedToPrevious": comparable_previous is not None,
        },
    }
