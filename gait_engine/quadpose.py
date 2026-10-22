"""QuadPose F2, a published quadruped pose model.

The checkpoint mapping and runtime are verified against the published file;
SilverPaws gait metrics remain experimental until evaluated on labeled dog-
walking clips. Heatmap peak scores are not calibrated probabilities.

The checkpoint is ``models/quadpose_f2.onnx`` from
https://github.com/EstevanSL/snapml-quadruped-pose at commit
52f0329b5c9af513b5a8f2820aaea6bbd945d0c0. Copyright 2026 Sausage Labs,
Apache-2.0. The publisher states that it was trained on AP-10K (Yu et al.,
NeurIPS 2021; annotations CC BY 4.0). This repository does not train or
fine-tune it.

The published ONNX graph expects a 256×256 RGB crop in 0–255, NCHW, and
returns a 17×64×64 heatmap. Decoding follows the publisher's reference decoder:
a square crop with 1.25 padding, no UDP, and DARK sub-pixel refinement. The
main pipeline crops to the selected RT-DETR dog box. The standalone video
diagnostic helper can use a frame-difference region when it has no detector
box; that fallback is not used to select the main pipeline's target dog.

Keypoints are AP-10K order. Hind paws (``L_B_Paw``, ``R_B_Paw``) are what the
rest of the app stores as left and right ankle motion. Hips (``L_Hip``,
``R_Hip``) are what it stores as hip stability. Left and right stay separate.
A point below the caller's confidence gate is stored with confidence 0 so the
metric layer can leave that measurement unset.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

import cv2
import numpy as np

PIPELINE_ID = "quadpose"
MODEL_NAME = "QuadPose F2"
# Commit that published models/quadpose_f2.onnx. The file hash is checked too.
MODEL_VERSION = "52f0329b5c9af513"
CHECKPOINT_URL = (
    "https://raw.githubusercontent.com/EstevanSL/snapml-quadruped-pose/"
    "52f0329b5c9af513b5a8f2820aaea6bbd945d0c0/models/quadpose_f2.onnx"
)
CHECKPOINT_SHA256 = "f3807433962d8abcee18f1bd45e5ff9e56bd899768b03a6996c3db4ebd12b884"
CHECKPOINT_FILENAME = "quadpose_f2.onnx"

POSE_INPUT = 256
HEATMAP = 64
HEATMAP_STRIDE = POSE_INPUT / HEATMAP
BBOX_PADDING = 1.25

# AP-10K joint order, using the dataset's names.
KEYPOINT_NAMES = (
    "L_Eye",
    "R_Eye",
    "Nose",
    "Neck",
    "Root of tail",
    "L_Shoulder",
    "L_Elbow",
    "L_F_Paw",
    "R_Shoulder",
    "R_Elbow",
    "R_F_Paw",
    "L_Hip",
    "L_Knee",
    "L_B_Paw",
    "R_Hip",
    "R_Knee",
    "R_B_Paw",
)

LEFT_HIND_PAW_INDEX = KEYPOINT_NAMES.index("L_B_Paw")
RIGHT_HIND_PAW_INDEX = KEYPOINT_NAMES.index("R_B_Paw")
LEFT_HIP_INDEX = KEYPOINT_NAMES.index("L_Hip")
RIGHT_HIP_INDEX = KEYPOINT_NAMES.index("R_Hip")

# Frame-difference crop. Not a learned detector.
MOTION_DIFF_THRESHOLD = 24
MIN_MOTION_PIXELS = 30
MIN_BOX_AREA_FRACTION = 0.04
MAX_BOX_AREA_FRACTION = 0.90

_SESSION = None


def cache_path() -> Path:
    """File that holds the pinned ONNX checkpoint."""

    configured = os.environ.get("SILVERPAWS_QUADPOSE_CACHE")
    if configured:
        path = Path(configured)
        if path.suffix == ".onnx":
            return path
        return path / CHECKPOINT_FILENAME
    return Path(__file__).resolve().parents[1] / "models" / "quadpose" / CHECKPOINT_FILENAME


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_checkpoint() -> Path:
    """Download the pinned checkpoint when the cache is empty or mismatched."""

    destination = cache_path()
    if destination.is_file() and _sha256(destination) == CHECKPOINT_SHA256:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".onnx.partial")
    try:
        urllib.request.urlretrieve(CHECKPOINT_URL, temporary)
        actual = _sha256(temporary)
        if actual != CHECKPOINT_SHA256:
            raise RuntimeError(
                "Downloaded QuadPose checkpoint hash "
                f"{actual} does not match the pinned {CHECKPOINT_SHA256}."
            )
        temporary.replace(destination)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return destination


def load_quadpose():
    """Load only a verified local checkpoint; setup must download weights explicitly."""

    global _SESSION
    if _SESSION is not None:
        return _SESSION
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError(
            "QuadPose needs onnxruntime. Install requirements.txt before running pose."
        ) from exc

    path = cache_path()
    if not path.is_file():
        raise RuntimeError(
            f"QuadPose weights are missing at {path}. Run "
            "'python scripts/cache_models.py' before enabling pose analysis."
        )
    actual = _sha256(path)
    if actual != CHECKPOINT_SHA256:
        raise RuntimeError(
            f"QuadPose checkpoint checksum mismatch at {path}; run "
            "'python scripts/cache_models.py' to replace it with the pinned file."
        )
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if not inputs or not outputs:
        raise RuntimeError("QuadPose checkpoint has no ONNX input or output.")
    _SESSION = session
    return _SESSION


def _gaussian_kernel1d(ksize: int = 5, sigma: float = 1.0) -> np.ndarray:
    radius = (ksize - 1) // 2
    positions = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-(positions ** 2) / (2.0 * sigma ** 2))
    return kernel / kernel.sum()


def _blur_heatmap(heatmap: np.ndarray) -> np.ndarray:
    """Separable blur, then restore each channel's original peak value."""

    kernel = _gaussian_kernel1d()
    blurred = np.empty_like(heatmap, dtype=np.float64)
    for index in range(heatmap.shape[0]):
        channel = heatmap[index]
        filtered = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="same"), 1, channel)
        filtered = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="same"), 0, filtered)
        peak = float(channel.max())
        blurred_peak = float(filtered.max())
        blurred[index] = filtered * (peak / blurred_peak) if blurred_peak > 1e-10 else filtered
    return blurred


def _refine_dark(coords: np.ndarray, heatmap: np.ndarray) -> np.ndarray:
    """One Newton step on the log heatmap. Rejects border and unstable peaks."""

    refined = coords.copy()
    log_heatmap = np.log(np.maximum(heatmap, 1e-10))
    _, height, width = heatmap.shape
    for index in range(coords.shape[0]):
        x = int(coords[index, 0])
        y = int(coords[index, 1])
        if not (1 <= x < width - 1 and 1 <= y < height - 1):
            continue
        dx = 0.5 * (log_heatmap[index, y, x + 1] - log_heatmap[index, y, x - 1])
        dy = 0.5 * (log_heatmap[index, y + 1, x] - log_heatmap[index, y - 1, x])
        dxx = log_heatmap[index, y, x + 1] - 2.0 * log_heatmap[index, y, x] + log_heatmap[index, y, x - 1]
        dyy = log_heatmap[index, y + 1, x] - 2.0 * log_heatmap[index, y, x] + log_heatmap[index, y - 1, x]
        dxy = 0.25 * (
            log_heatmap[index, y + 1, x + 1]
            - log_heatmap[index, y + 1, x - 1]
            - log_heatmap[index, y - 1, x + 1]
            + log_heatmap[index, y - 1, x - 1]
        )
        determinant = dxx * dyy - dxy * dxy
        if abs(determinant) < 1e-12 or dxx >= 0.0 or dyy >= 0.0:
            continue
        offset_x = -(dyy * dx - dxy * dy) / determinant
        offset_y = -(dxx * dy - dxy * dx) / determinant
        if abs(offset_x) > 1.0 or abs(offset_y) > 1.0:
            continue
        refined[index, 0] += min(max(offset_x, -0.5), 0.5)
        refined[index, 1] += min(max(offset_y, -0.5), 0.5)
    return refined


def _decode_heatmap(heatmap: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(K, H, W) heatmap -> crop-pixel (x, y) and peak scores."""

    blurred = _blur_heatmap(heatmap)
    count, _, width = blurred.shape
    flat = blurred.reshape(count, -1)
    peaks = flat.argmax(axis=1)
    scores = flat[np.arange(count), peaks]
    coords = np.stack([peaks % width, peaks // width], axis=1).astype(np.float64)
    coords = _refine_dark(coords, blurred)
    return coords * HEATMAP_STRIDE, scores


def _compute_crop(bbox: np.ndarray) -> tuple[float, float, float]:
    values = np.asarray(bbox, dtype=np.float64).reshape(-1)
    if values.shape != (4,) or not np.isfinite(values).all():
        raise ValueError("Dog bounding box must contain four finite coordinates.")
    x1, y1, x2, y2 = (float(value) for value in values)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Dog bounding box must have positive width and height.")
    side = max(x2 - x1, y2 - y1) * BBOX_PADDING
    if not np.isfinite(side) or side <= 0:
        raise ValueError("Dog bounding box cannot produce a valid pose crop.")
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0, side


def _crop_frame(frame_bgr: np.ndarray, bbox: np.ndarray) -> tuple[np.ndarray, tuple[float, float, float]]:
    center_x, center_y, side = _compute_crop(bbox)
    scale = POSE_INPUT / side
    matrix = np.array(
        [
            [scale, 0, POSE_INPUT / 2 - scale * center_x],
            [0, scale, POSE_INPUT / 2 - scale * center_y],
        ],
        dtype=np.float32,
    )
    crop = cv2.warpAffine(
        frame_bgr,
        matrix,
        (POSE_INPUT, POSE_INPUT),
        flags=cv2.INTER_LINEAR,
        borderValue=(0, 0, 0),
    )
    return crop, (center_x, center_y, side)


def _crop_to_image(xy_input: np.ndarray, center_x: float, center_y: float, side: float) -> np.ndarray:
    return np.stack(
        [
            center_x + (xy_input[:, 0] / POSE_INPUT - 0.5) * side,
            center_y + (xy_input[:, 1] / POSE_INPUT - 0.5) * side,
        ],
        axis=1,
    )


def motion_bbox(frame_bgr: np.ndarray, previous_bgr: np.ndarray | None) -> np.ndarray:
    """Box around the pixels that changed, or the whole frame when that is not usable."""

    height, width = frame_bgr.shape[:2]
    full = np.array([0.0, 0.0, float(width), float(height)], dtype=np.float64)
    if previous_bgr is None or previous_bgr.shape[:2] != frame_bgr.shape[:2]:
        return full

    difference = cv2.absdiff(
        cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY),
        cv2.cvtColor(previous_bgr, cv2.COLOR_BGR2GRAY),
    )
    changed = difference >= MOTION_DIFF_THRESHOLD
    if int(np.count_nonzero(changed)) < MIN_MOTION_PIXELS:
        return full

    ys, xs = np.nonzero(changed)
    x1, x2 = float(xs.min()), float(xs.max() + 1)
    y1, y2 = float(ys.min()), float(ys.max() + 1)
    area = (x2 - x1) * (y2 - y1)
    frame_area = float(width * height)
    if area < MIN_BOX_AREA_FRACTION * frame_area or area > MAX_BOX_AREA_FRACTION * frame_area:
        return full
    return np.array([x1, y1, x2, y2], dtype=np.float64)


def _predict_frame(session, frame_bgr: np.ndarray, bbox: np.ndarray) -> np.ndarray:
    """Return one frame of (17, 3) keypoints as (y, x, confidence), normalized."""

    if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        raise ValueError("QuadPose expects a three-channel BGR frame.")
    height, width = frame_bgr.shape[:2]
    if width <= 0 or height <= 0:
        raise ValueError("Frame has no pixels.")
    crop, (center_x, center_y, side) = _crop_frame(frame_bgr, bbox)
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32)
    blob = rgb.transpose(2, 0, 1)[None]
    input_name = session.get_inputs()[0].name
    heatmap = np.asarray(session.run(None, {input_name: blob})[0], dtype=np.float32)[0]
    if heatmap.shape != (len(KEYPOINT_NAMES), HEATMAP, HEATMAP):
        raise RuntimeError(
            f"Unexpected QuadPose heatmap shape {heatmap.shape}; "
            f"expected {(len(KEYPOINT_NAMES), HEATMAP, HEATMAP)}."
        )

    crop_xy, scores = _decode_heatmap(heatmap)
    image_xy = _crop_to_image(crop_xy, center_x, center_y, side)
    keypoints = np.zeros((len(KEYPOINT_NAMES), 3), dtype=np.float32)
    for index in range(len(KEYPOINT_NAMES)):
        x_norm = float(image_xy[index, 0] / width)
        y_norm = float(image_xy[index, 1] / height)
        score = float(scores[index])
        if not np.isfinite(score):
            score = 0.0
        confidence = float(np.clip(score, 0.0, 1.0))
        inside = 0.0 <= x_norm <= 1.0 and 0.0 <= y_norm <= 1.0
        if not inside:
            confidence = 0.0
        keypoints[index, 0] = y_norm if inside else 0.0
        keypoints[index, 1] = x_norm if inside else 0.0
        keypoints[index, 2] = confidence
    return keypoints


def extract_keypoints_from_video(
    video_path: str | Path,
    session,
    *,
    min_confidence: float = 0.2,
    max_frames: int | None = None,
) -> tuple[np.ndarray, float]:
    """Run QuadPose on a video.

    ``min_confidence`` is accepted so the call matches the rest of the pipeline.
    The metric layer applies the gate. This function still returns every point,
    with confidence 0 when the point fell outside the frame.

    Returns ``(keypoints, fps)`` with keypoints shaped ``(frames, 17, 3)`` in
    ``(y, x, confidence)`` order, normalized to the source frame.
    """

    del min_confidence  # applied by metrics.py and features.py
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"OpenCV could not open video: {path}")

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not np.isfinite(fps) or fps <= 0:
        fps = 0.0

    frames: list[np.ndarray] = []
    previous: np.ndarray | None = None
    frame_number = 0
    try:
        while max_frames is None or frame_number < max_frames:
            success, frame = capture.read()
            if not success:
                break
            bbox = motion_bbox(frame, previous)
            frames.append(_predict_frame(session, frame, bbox))
            previous = frame
            frame_number += 1
    finally:
        capture.release()

    if not frames:
        raise ValueError(f"No readable frames were found in video: {path}")
    return np.stack(frames, axis=0), fps
