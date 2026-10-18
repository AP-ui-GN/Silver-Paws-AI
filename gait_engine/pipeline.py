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

import cv2

from .clip_quality import quality_notes
from .confidence import pose_is_trusted, summarize_keypoints
from .features import MOTION_FLOOR, hip_stability, motion_statistics
from .metrics import compute_gait_metrics
from .motion import read_motion_signal
from .movenet import DEFAULT_MODEL_URL, MOVENET_MODEL_NAME, MOVENET_MODEL_VERSION
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


def _pose_model_identity(model_url: str | None) -> tuple[str, str]:
    """Name and version for the pose model that was actually requested.

    A different URL is not labeled as MoveNet Thunder. The fallback path never
    claims to be pose.
    """

    url = (model_url or DEFAULT_MODEL_URL).rstrip("/")
    if url == DEFAULT_MODEL_URL.rstrip("/"):
        return MOVENET_MODEL_NAME, MOVENET_MODEL_VERSION
    return "MoveNet", url


def _model_info(pipeline: str, model_url: str | None) -> dict[str, str]:
    """Describe the model that produced this result. Inference stays on the server."""

    if pipeline == "movenet":
        name, version = _pose_model_identity(model_url)
        return {
            "pipeline": "movenet",
            "modelName": name,
            "modelVersion": version,
            "runsOn": "server",
        }

    return {
        "pipeline": "opencv-motion",
        "modelName": "OpenCV frame difference",
        "modelVersion": cv2.__version__,
        "runsOn": "server",
    }


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
    model_confidence: float | None = None
    frames_used: int | None = None
    frames_total: int | None = None
    low_confidence = False

    if use_pose:
        keypoints, pose_skip_reason = _try_pose(
            path,
            model_url=model_url,
            max_frames=MAX_POSE_FRAMES,
        )
        if keypoints is not None:
            pipeline = "movenet"
            summary = summarize_keypoints(
                keypoints,
                frame_threshold=MIN_POSE_CONFIDENCE,
            )
            model_confidence = summary["modelConfidence"]
            frames_used = summary["framesUsed"]
            frames_total = summary["framesTotal"]
            measurements["meanKeypointConfidence"] = model_confidence
            # Below the trust line, limb numbers are left unset. They are not
            # published as zero, and the result UI shows "Not measured".
            if pose_is_trusted(summary, minimum=MIN_POSE_CONFIDENCE):
                gait = compute_gait_metrics(
                    keypoints,
                    confidence_threshold=POSE_CONFIDENCE_THRESHOLD,
                )
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
            else:
                low_confidence = True

    signal_quality, signal_note = _assess_signal(pipeline, measurements)
    if low_confidence and signal_quality != "unusable":
        signal_quality = "limited"
        signal_note = (
            "Pose landmarks were found, but confidence was too low to measure the legs. "
            "Try a clearer clip, filmed from the side with the whole body in frame."
        )

    notes = quality_notes(
        frames_read=signal.frames_read,
        fps=signal.fps,
        duration_seconds=signal.duration_seconds,
        width=signal.width,
        height=signal.height,
        brightness=signal.brightness,
        motion_mean=motion_mean,
        motion_coverage=motion_coverage,
    )

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

    # historical_change_factor returns None on a first walk. When that factor
    # has a weight, the overall indicator is recomputed so the comparison counts.
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
        "modelInfo": _model_info(pipeline, model_url),
        "modelConfidence": model_confidence,
        "framesUsed": frames_used,
        "framesTotal": frames_total,
        "lowConfidence": low_confidence,
        "qualityNotes": notes,
        "diagnostics": {
            "fps": signal.fps,
            "framePairs": len(signal.frame_motion),
            "poseSkipReason": pose_skip_reason,
            "configuredWeights": DEFAULT_WEIGHTS,
            "comparedToPrevious": comparable_previous is not None,
        },
    }
