"""MoveNet Thunder loading and video keypoint extraction.

This module intentionally has no FastAPI or database dependencies. Keeping
inference here makes it possible to validate the model in Colab before the
backend is introduced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

DEFAULT_MODEL_URL = "https://tfhub.dev/google/movenet/singlepose/thunder/4"
MODEL_INPUT_SIZE = 256

# MoveNet's output order. The model was trained on human pose data; these
# labels are retained because they are part of the pretrained model contract.
KEYPOINT_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)


def load_movenet(model_url: str = DEFAULT_MODEL_URL) -> Any:
    """Download/load MoveNet Thunder and return its serving signature.

    TensorFlow and TensorFlow Hub are imported lazily so metric-only unit tests
    and documentation tooling do not need the heavyweight ML dependencies.
    """

    try:
        import tensorflow as tf
        import tensorflow_hub as hub
    except ImportError as exc:
        raise RuntimeError(
            "MoveNet dependencies are missing. Install requirements.txt with "
            "Python 3.10 or 3.11 before running validation."
        ) from exc

    loaded_model = hub.load(model_url)
    if hasattr(loaded_model, "signatures") and "serving_default" in loaded_model.signatures:
        return loaded_model.signatures["serving_default"]

    # This fallback supports local/saved models that expose __call__ directly.
    if callable(loaded_model):
        return loaded_model

    raise RuntimeError(f"Loaded model at {model_url!r} has no callable signature.")


def _predict_frame(model: Any, frame_bgr: np.ndarray) -> np.ndarray:
    """Run one BGR OpenCV frame through MoveNet and return (17, 3) keypoints."""

    import tensorflow as tf

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    input_tensor = tf.image.resize_with_pad(
        tf.expand_dims(frame_rgb, axis=0),
        MODEL_INPUT_SIZE,
        MODEL_INPUT_SIZE,
    )
    # MoveNet expects an int32 tensor for the TF Hub single-pose model.
    input_tensor = tf.cast(input_tensor, dtype=tf.int32)
    outputs = model(input_tensor)

    if isinstance(outputs, dict):
        if "output_0" in outputs:
            output = outputs["output_0"]
        else:
            output = next(iter(outputs.values()))
    else:
        output = outputs

    keypoints = np.asarray(output)
    # Thunder normally returns (1, 1, 17, 3). Accept equivalent leading
    # singleton dimensions so saved/local signatures remain easy to use.
    keypoints = np.squeeze(keypoints)
    if keypoints.shape != (len(KEYPOINT_NAMES), 3):
        raise ValueError(
            "Unexpected MoveNet output shape "
            f"{keypoints.shape}; expected ({len(KEYPOINT_NAMES)}, 3)."
        )
    # Copy because TensorFlow can expose its NumPy view as read-only, while
    # downstream confidence masking intentionally annotates low-confidence
    # coordinates with NaN.
    return keypoints.astype(np.float32, copy=True)


def extract_keypoints_from_video(
    video_path: str | Path,
    model: Any,
    *,
    min_confidence: float = 0.2,
    max_frames: int | None = None,
) -> tuple[np.ndarray, float]:
    """Extract MoveNet keypoints for a video.

    Returns:
        A tuple of ``(keypoints, fps)``. Keypoints have shape
        ``(frames, 17, 3)`` and store ``(y, x, confidence)`` values normalized
        to the frame dimensions.
    """

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be between 0 and 1.")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open video: {path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not np.isfinite(fps) or fps <= 0:
        fps = 0.0

    frames: list[np.ndarray] = []
    frame_number = 0
    try:
        while max_frames is None or frame_number < max_frames:
            success, frame = capture.read()
            if not success:
                break

            # Keep raw coordinates and confidence values in the output. The
            # metric layer applies min_confidence when deciding which points
            # are usable, so saved JSON remains useful for later inspection.
            frames.append(_predict_frame(model, frame))
            frame_number += 1
    finally:
        capture.release()

    if not frames:
        raise ValueError(f"No readable frames were found in video: {path}")

    return np.stack(frames, axis=0), fps
