"""RTMPose-m animal pose for one dog in a clip.

The checkpoint is OpenMMLab's published RTMPose-m trained on AP-10K
(``rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206``).
SilverPaws did not train it. Keypoint names and order are the AP-10K
labels from the MMPose dataset meta, not a human skeleton.
"""

from __future__ import annotations

import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np

MODEL_NAME = "RTMPose-m"
MODEL_VERSION = "rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206"
PIPELINE_ID = "rtmpose-ap10k"
ONNX_FILENAME = f"{MODEL_VERSION}.onnx"
ONNX_URL = (
    "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/"
    f"{MODEL_VERSION}.zip"
)

# MMPose config rtmpose-m_8xb64-210e_ap10k-256x256: 256x256 input, SimCC
# split ratio 2, ImageNet normalization, RGB.
INPUT_SIZE = 256
SIMCC_SPLIT_RATIO = 2.0
BBOX_PADDING = 1.25
_MEAN = np.array([123.675, 116.28, 103.53], dtype=np.float32)
_STD = np.array([58.395, 57.12, 57.375], dtype=np.float32)

# Order from MMPose configs/_base_/datasets/ap10k.py and the AP-10K keypoint table.
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

L_HIP_INDEX = KEYPOINT_NAMES.index("L_Hip")
R_HIP_INDEX = KEYPOINT_NAMES.index("R_Hip")
L_FORE_PAW_INDEX = KEYPOINT_NAMES.index("L_F_Paw")
R_FORE_PAW_INDEX = KEYPOINT_NAMES.index("R_F_Paw")
L_HIND_PAW_INDEX = KEYPOINT_NAMES.index("L_B_Paw")
R_HIND_PAW_INDEX = KEYPOINT_NAMES.index("R_B_Paw")


def cache_directory() -> Path:
    """Directory that holds the RTMPose ONNX file."""

    configured = os.environ.get("SILVERPAWS_RTMPOSE_CACHE")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "models" / "rtmpose"


def cached_model_path() -> Path:
    return cache_directory() / ONNX_FILENAME


def ensure_model_file(destination: Path | None = None) -> Path:
    """Return the official ONNX file, downloading the published zip once."""

    path = destination or cached_model_path()
    if path.is_file() and path.stat().st_size > 0:
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    archive_path = path.with_suffix(".zip")
    request = urllib.request.Request(ONNX_URL, headers={"User-Agent": "SilverPaws/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            archive_path.write_bytes(response.read())
    except Exception as exc:  # noqa: BLE001 - caller falls back to picture motion
        archive_path.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download RTMPose-m AP-10K: {exc}") from exc

    try:
        with zipfile.ZipFile(archive_path) as archive:
            member = next(
                (name for name in archive.namelist() if name.endswith("end2end.onnx")),
                None,
            )
            if member is None:
                raise RuntimeError("The RTMPose zip did not contain end2end.onnx.")
            info = archive.getinfo(member)
            if info.file_size > 200_000_000:
                raise RuntimeError("The RTMPose ONNX file is larger than expected.")
            path.write_bytes(archive.read(member))
    finally:
        archive_path.unlink(missing_ok=True)

    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("The RTMPose ONNX file was not saved.")
    return path


def describe_model(path: Path) -> tuple[str, str]:
    """Name and version for the file that actually loaded."""

    if path.name == ONNX_FILENAME:
        return MODEL_NAME, MODEL_VERSION
    raise RuntimeError(
        "Refusing to label a different file as the published RTMPose-m AP-10K checkpoint."
    )


def load_quadruped(model_path: str | Path | None = None) -> tuple[Any, Path]:
    """Load the published ONNX checkpoint. Returns (session, path)."""

    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError(
            "ONNX Runtime is missing. Install requirements.txt before running pose."
        ) from exc

    path = Path(model_path) if model_path else ensure_model_file()
    if not path.is_file():
        raise RuntimeError(f"RTMPose file not found: {path}")
    describe_model(path)
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    return session, path


def _warp_matrix(center: np.ndarray, scale: np.ndarray) -> np.ndarray:
    """Affine matrix used by MMPose top-down crop into the 256x256 input."""

    src_w = float(scale[0])
    src_dir = np.array([0.0, src_w * -0.5], dtype=np.float32)
    dst_dir = np.array([0.0, INPUT_SIZE * -0.5], dtype=np.float32)
    src = np.zeros((3, 2), dtype=np.float32)
    src[0] = center
    src[1] = center + src_dir
    direction = src[0] - src[1]
    src[2] = src[1] + np.array([-direction[1], direction[0]], dtype=np.float32)

    dst = np.zeros((3, 2), dtype=np.float32)
    dst[0] = [INPUT_SIZE * 0.5, INPUT_SIZE * 0.5]
    dst[1] = np.array([INPUT_SIZE * 0.5, INPUT_SIZE * 0.5], dtype=np.float32) + dst_dir
    direction = dst[0] - dst[1]
    dst[2] = dst[1] + np.array([-direction[1], direction[0]], dtype=np.float32)
    return cv2.getAffineTransform(src, dst)


def _predict_frame(session: Any, frame_bgr: np.ndarray) -> np.ndarray:
    """Run one BGR frame. Returns (17, 3) as (y, x, confidence), frame-normalized."""

    height, width = frame_bgr.shape[:2]
    if width <= 0 or height <= 0:
        raise ValueError("Frame has no pixels.")

    center = np.array([width * 0.5, height * 0.5], dtype=np.float32)
    scale = np.array([width * BBOX_PADDING, height * BBOX_PADDING], dtype=np.float32)
    # Square crop: the model input is square, so the longer side sets both.
    longer = float(max(scale[0], scale[1]))
    scale = np.array([longer, longer], dtype=np.float32)
    warped = cv2.warpAffine(
        cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB),
        _warp_matrix(center, scale),
        (INPUT_SIZE, INPUT_SIZE),
        flags=cv2.INTER_LINEAR,
    )
    normalized = (warped.astype(np.float32) - _MEAN) / _STD
    model_input = np.ascontiguousarray(normalized.transpose(2, 0, 1)[None], dtype=np.float32)
    simcc_x, simcc_y = session.run(None, {session.get_inputs()[0].name: model_input})
    if simcc_x.shape[1] != len(KEYPOINT_NAMES) or simcc_y.shape[1] != len(KEYPOINT_NAMES):
        raise ValueError(
            "Unexpected RTMPose keypoint count "
            f"{simcc_x.shape}; expected {len(KEYPOINT_NAMES)} AP-10K points."
        )

    flat_x = simcc_x.reshape(len(KEYPOINT_NAMES), -1)
    flat_y = simcc_y.reshape(len(KEYPOINT_NAMES), -1)
    locs_x = np.argmax(flat_x, axis=1).astype(np.float32)
    locs_y = np.argmax(flat_y, axis=1).astype(np.float32)
    scores = 0.5 * (np.max(flat_x, axis=1) + np.max(flat_y, axis=1))
    # SimCC bin index -> input pixels -> original frame.
    pixels = np.stack((locs_x, locs_y), axis=-1) / SIMCC_SPLIT_RATIO
    pixels = pixels / INPUT_SIZE * scale
    pixels = pixels + center - scale / 2

    keypoints = np.empty((len(KEYPOINT_NAMES), 3), dtype=np.float32)
    keypoints[:, 0] = pixels[:, 1] / float(height)
    keypoints[:, 1] = pixels[:, 0] / float(width)
    finite_scores = np.where(np.isfinite(scores), scores, 0.0)
    keypoints[:, 2] = np.clip(finite_scores, 0.0, 1.0)
    return keypoints


def extract_keypoints_from_video(
    video_path: str | Path,
    session: Any,
    *,
    max_frames: int | None = None,
) -> tuple[np.ndarray, float]:
    """Return ``(frames, 17, 3)`` AP-10K keypoints and the clip frame rate.

    Coordinates are normalized to the source frame, origin at the top left.
    Confidence is the SimCC score clamped to 0-1. A low score stays low.
    """

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
    frame_number = 0
    try:
        while max_frames is None or frame_number < max_frames:
            success, frame = capture.read()
            if not success:
                break
            frames.append(_predict_frame(session, frame))
            frame_number += 1
    finally:
        capture.release()

    if not frames:
        raise ValueError(f"No readable frames were found in video: {path}")

    return np.stack(frames, axis=0), fps
