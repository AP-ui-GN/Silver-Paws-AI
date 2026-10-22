"""Dog detection, temporal association, and QuadPose F2 canine landmarks.

RT-DETR detects dogs and the existing temporal tracker preserves a selected
identity. QuadPose F2 estimates AP-10K-order animal landmarks inside that
tracked box. The checkpoint is pinned and checksum-verified; model heatmap
scores are not calibrated probabilities. The gait formulas remain experimental
until tested against a labeled dog-walking dataset. Pose failure falls back to
the independently measured OpenCV picture-motion signal.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .quadpose import MODEL_NAME as QUADPOSE_MODEL_NAME, MODEL_VERSION as QUADPOSE_MODEL_VERSION
from .sampling import DETECT_EVERY_N_FRAMES, SampledFrame
from .tracking import associate_tracks, choose_initial_dog, choose_tracked_dog

DETECTOR_ID = "PekingU/rtdetr_r50vd_coco_o365"
POSE_ID = QUADPOSE_MODEL_NAME
POSE_REVISION = QUADPOSE_MODEL_VERSION
DOG_DETECT_THRESHOLD = 0.3
KEYPOINT_MIN_SCORE = 0.3
CROP_EXPAND = 0.25
POSE_BATCH = 8

# AP-10K order. Do not read this from the human checkpoint labels.
AP10K_KEYPOINTS: tuple[str, ...] = (
    "left_eye",
    "right_eye",
    "nose",
    "neck",
    "root_of_tail",
    "left_shoulder",
    "left_elbow",
    "left_front_paw",
    "right_shoulder",
    "right_elbow",
    "right_front_paw",
    "left_hip",
    "left_knee",
    "left_back_paw",
    "right_hip",
    "right_knee",
    "right_back_paw",
)

LEFT_EYE = 0
RIGHT_EYE = 1
NOSE = 2
NECK = 3
ROOT_OF_TAIL = 4
LEFT_SHOULDER = 5
LEFT_ELBOW = 6
LEFT_FRONT_PAW = 7
RIGHT_SHOULDER = 8
RIGHT_ELBOW = 9
RIGHT_FRONT_PAW = 10
LEFT_HIP = 11
LEFT_KNEE = 12
LEFT_BACK_PAW = 13
RIGHT_HIP = 14
RIGHT_KNEE = 15
RIGHT_BACK_PAW = 16

# Left/right counterparts. Applied when a frame is mirrored, not on every
# detection. The model is asked for the AP-10K order above.
AP10K_SWAP_PAIRS: tuple[tuple[int, int], ...] = (
    (LEFT_EYE, RIGHT_EYE),
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_ELBOW, RIGHT_ELBOW),
    (LEFT_FRONT_PAW, RIGHT_FRONT_PAW),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_KNEE, RIGHT_KNEE),
    (LEFT_BACK_PAW, RIGHT_BACK_PAW),
)

# Legacy COCO-17 names are retained only to interpret old saved results and
# setup history. New pose results use the verified AP-10K-order QuadPose head.
COCO17_KEYPOINTS: tuple[str, ...] = (
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
COCO17_EDGES: tuple[tuple[int, int], ...] = (
    (15, 13),
    (13, 11),
    (16, 14),
    (14, 12),
    (11, 12),
    (5, 11),
    (6, 12),
    (5, 6),
    (5, 7),
    (6, 8),
    (7, 9),
    (8, 10),
    (1, 2),
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
    (3, 5),
    (4, 6),
)
MODEL_OUTPUT_SCHEMA = "ap10k"
MODEL_OUTPUT_KEYPOINTS = AP10K_KEYPOINTS
SCHEMA_LIMIT = (
    "The AP-10K landmarks are model estimates. Gait metrics are experimental "
    "and have not been validated on a labeled dog-walking dataset."
)

# Anatomical links for an AP-10K array. These are not the checkpoint edges.
AP10K_SKELETON_EDGES: tuple[tuple[int, int], ...] = (
    (LEFT_EYE, NOSE),
    (RIGHT_EYE, NOSE),
    (NOSE, NECK),
    (NECK, ROOT_OF_TAIL),
    (NECK, LEFT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (LEFT_ELBOW, LEFT_FRONT_PAW),
    (NECK, RIGHT_SHOULDER),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (RIGHT_ELBOW, RIGHT_FRONT_PAW),
    (ROOT_OF_TAIL, LEFT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_BACK_PAW),
    (ROOT_OF_TAIL, RIGHT_HIP),
    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_BACK_PAW),
)

MODEL_OUTPUT_EDGES = AP10K_SKELETON_EDGES


def hf_home() -> Path:
    """Directory for Hugging Face weights. Defaults to ``models/hf``."""

    configured = os.environ.get("HF_HOME")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "models" / "hf"


def swap_left_right(keypoints: np.ndarray) -> np.ndarray:
    """Exchange the AP-10K left/right pairs. ``keypoints`` is (..., 17, 3)."""

    swapped = np.array(keypoints, copy=True)
    for left, right in AP10K_SWAP_PAIRS:
        swapped[..., left, :], swapped[..., right, :] = (
            swapped[..., right, :].copy(),
            swapped[..., left, :].copy(),
        )
    return swapped


@dataclass(frozen=True)
class PoseResult:
    """Pose for the sampled frames.

    ``keypoints`` is ``(frames, 17, 3)`` of ``(x_px, y_px, score)`` in the
    source frame after rotation. A missing point is NaN in x and y with
    score 0. ``boxes`` is one detector ``(x, y, width, height)`` per frame,
    or None when that frame had no dog box. ``timestamps_seconds`` lines up
    with frames.
    """

    keypoints: np.ndarray
    boxes: list[tuple[float, float, float, float] | None]
    timestamps_seconds: np.ndarray
    dog_frames_share: float
    multiple_dogs: bool
    person_present: bool
    detector_id: str
    pose_id: str
    detector_revision: str | None
    pose_revision: str | None
    keypoint_schema: str = MODEL_OUTPUT_SCHEMA
    track_states: tuple[str, ...] = ()
    track_segment_ids: tuple[int | None, ...] = ()


class PoseBackend(ABC):
    """One pose implementation. ``process`` does not catch its own failures."""

    @abstractmethod
    def process(self, frames: list[SampledFrame]) -> PoseResult:
        """Return keypoints for already-sampled frames."""


def crop_from_keypoints(
    keypoints: np.ndarray,
    width: int,
    height: int,
    *,
    min_score: float = KEYPOINT_MIN_SCORE,
    expand: float = CROP_EXPAND,
) -> tuple[float, float, float, float] | None:
    """Bounding box around valid keypoints, expanded by ``expand`` on each side."""

    if keypoints.shape != (len(AP10K_KEYPOINTS), 3):
        return None
    valid = np.isfinite(keypoints[:, 0]) & np.isfinite(keypoints[:, 1]) & (keypoints[:, 2] >= min_score)
    if int(np.count_nonzero(valid)) < 2:
        return None
    xs = keypoints[valid, 0]
    ys = keypoints[valid, 1]
    x1, x2 = float(np.min(xs)), float(np.max(xs))
    y1, y2 = float(np.min(ys)), float(np.max(ys))
    box_w = max(1.0, x2 - x1)
    box_h = max(1.0, y2 - y1)
    x1 -= box_w * expand
    x2 += box_w * expand
    y1 -= box_h * expand
    y2 += box_h * expand
    x1 = min(max(0.0, x1), max(0, width - 1))
    y1 = min(max(0.0, y1), max(0, height - 1))
    x2 = min(max(x1 + 1.0, x2), float(width))
    y2 = min(max(y1 + 1.0, y2), float(height))
    return (x1, y1, x2 - x1, y2 - y1)


def normalize_to_box(
    x: float, y: float, box: tuple[float, float, float, float]
) -> tuple[float, float]:
    """Map a source-frame pixel into a COCO box, as fractions of that box."""

    origin_x, origin_y, width, height = box
    return (x - origin_x) / width, (y - origin_y) / height


def denormalize_from_box(
    x: float, y: float, box: tuple[float, float, float, float]
) -> tuple[float, float]:
    """Map a box fraction back to a source-frame pixel."""

    origin_x, origin_y, width, height = box
    return origin_x + x * width, origin_y + y * height


def dog_boxes_from_detections(
    labels,
    scores,
    xyxy,
    *,
    dog_id: int,
    person_id: int | None,
    threshold: float,
) -> tuple[list[tuple[float, float, float, float]], int, bool]:
    """Keep dog boxes. A person box is recorded and is not returned as the dog."""

    dogs: list[tuple[float, float, float, float]] = []
    dog_count = 0
    saw_person = False
    for label, score, box in zip(labels, scores, xyxy):
        if float(score) < threshold:
            continue
        coco = (
            float(box[0]),
            float(box[1]),
            float(box[2] - box[0]),
            float(box[3] - box[1]),
        )
        if int(label) == int(dog_id):
            dog_count += 1
            if coco[2] > 1 and coco[3] > 1:
                dogs.append(coco)
        elif person_id is not None and int(label) == int(person_id):
            saw_person = True
    return dogs, dog_count, saw_person


def _empty_keypoints(count: int) -> np.ndarray:
    array = np.full((count, len(AP10K_KEYPOINTS), 3), np.nan, dtype=np.float32)
    array[:, :, 2] = 0.0
    return array


class QuadPoseBackend(PoseBackend):
    """Run RT-DETR plus the pinned QuadPose F2 model; load each once per process."""

    def __init__(self) -> None:
        self._loaded = False
        self._device = "cpu"
        self._detector = None
        self._detector_processor = None
        self._pose = None
        self._dog_id: int | None = None
        self._person_id: int | None = None
        self._detector_revision: str | None = None
        self._pose_revision: str | None = None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        home = hf_home()
        home.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(home)

        import torch
        from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        # Inference must be reproducible/offline once setup is complete.
        # Model downloads belong to scripts/cache_models.py, not user uploads.
        self._detector_processor = RTDetrImageProcessor.from_pretrained(
            DETECTOR_ID, local_files_only=True
        )
        self._detector = RTDetrForObjectDetection.from_pretrained(
            DETECTOR_ID, local_files_only=True
        )
        self._detector.to(self._device)
        self._detector.eval()
        labels = {value: key for key, value in self._detector.config.id2label.items()}
        if "dog" not in labels:
            raise RuntimeError("RT-DETR checkpoint does not declare a dog class.")
        self._dog_id = labels["dog"]
        self._person_id = labels.get("person")

        # Pose weights must be installed explicitly. Inference never downloads
        # a large checkpoint as an unexpected side effect of an upload.
        from .quadpose import load_quadpose
        self._pose = load_quadpose()
        self._detector_revision = _revision(DETECTOR_ID)
        self._pose_revision = POSE_REVISION
        self._loaded = True

    def process(self, frames: list[SampledFrame]) -> PoseResult:
        if not frames:
            raise ValueError("No frames were sampled.")
        self._ensure_loaded()

        keypoints = _empty_keypoints(len(frames))
        observations: list[list[tuple[float, float, float, float]]] = []
        multiple_dogs = False
        person_present = False

        # The detector runs on a fixed stride. Frames in between are empty
        # observations. Tracking does not copy the last box into that gap.
        for index, frame in enumerate(frames):
            if index % DETECT_EVERY_N_FRAMES != 0:
                observations.append([])
                continue
            detected, dog_count, saw_person = self._detect(frame)
            multiple_dogs = multiple_dogs or dog_count > 1
            person_present = person_present or saw_person
            observations.append(detected)

        decisions = associate_tracks(observations)
        if any(decision.state == "ambiguous" for decision in decisions):
            multiple_dogs = True
        boxes: list[tuple[float, float, float, float] | None] = [
            decision.box if decision.state in ("tracked", "new_segment") else None
            for decision in decisions
        ]
        ready = [index for index, box in enumerate(boxes) if box is not None]
        for start in range(0, len(ready), POSE_BATCH):
            self._pose_chunk(frames, boxes, ready[start : start + POSE_BATCH], keypoints)

        dog_frames = sum(1 for box in boxes if box is not None)
        share = dog_frames / len(frames)

        return PoseResult(
            keypoints=keypoints,
            boxes=boxes,
            timestamps_seconds=np.asarray(
                [frame.timestamp_seconds for frame in frames], dtype=np.float64
            ),
            dog_frames_share=round(share, 4),
            multiple_dogs=multiple_dogs,
            person_present=person_present,
            detector_id=DETECTOR_ID,
            pose_id=POSE_ID,
            detector_revision=self._detector_revision,
            pose_revision=self._pose_revision,
            keypoint_schema=MODEL_OUTPUT_SCHEMA,
            track_states=tuple(decision.state for decision in decisions),
            track_segment_ids=tuple(decision.segment_id for decision in decisions),
        )

    def _pose_chunk(
        self,
        frames: list[SampledFrame],
        boxes: list[tuple[float, float, float, float] | None],
        indexes: list[int],
        keypoints: np.ndarray,
    ) -> None:
        chunk_boxes = [boxes[index] for index in indexes]
        if any(box is None for box in chunk_boxes):
            return
        self._run_pose_batch(frames, chunk_boxes, indexes, keypoints)  # type: ignore[arg-type]

    def _detect(
        self, frame: SampledFrame
    ) -> tuple[list[tuple[float, float, float, float]], int, bool]:
        import torch
        from PIL import Image

        assert self._detector is not None
        assert self._detector_processor is not None
        assert self._dog_id is not None
        image = Image.fromarray(frame.image_bgr[:, :, ::-1])
        inputs = self._detector_processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self._device) for key, value in inputs.items()}
        with torch.inference_mode():
            outputs = self._detector(**inputs)
        results = self._detector_processor.post_process_object_detection(
            outputs,
            target_sizes=[(frame.height, frame.width)],
            threshold=DOG_DETECT_THRESHOLD,
        )[0]
        labels = results["labels"].detach().cpu().numpy()
        scores = results["scores"].detach().cpu().numpy()
        xyxy = results["boxes"].detach().cpu().numpy()
        return dog_boxes_from_detections(
            labels,
            scores,
            xyxy,
            dog_id=int(self._dog_id),
            person_id=None if self._person_id is None else int(self._person_id),
            threshold=DOG_DETECT_THRESHOLD,
        )

    def _run_pose_batch(
        self,
        frames: list[SampledFrame],
        boxes: list[tuple[float, float, float, float]],
        indexes: list[int],
        keypoints: np.ndarray,
    ) -> None:
        """Estimate AP-10K landmarks in the selected dog's detector crop."""

        from .quadpose import _predict_frame

        if self._pose is None:
            raise RuntimeError("QuadPose session is not initialized.")
        for index, box in zip(indexes, boxes):
            frame = frames[index]
            x, y, width, height = (float(value) for value in box)
            if not np.isfinite([x, y, width, height]).all() or width <= 1 or height <= 1:
                continue
            xyxy = np.asarray([x, y, x + width, y + height], dtype=np.float64)
            predicted = _predict_frame(self._pose, frame.image_bgr, xyxy)
            if predicted.shape != (len(AP10K_KEYPOINTS), 3):
                raise RuntimeError(
                    f"QuadPose returned {predicted.shape}; expected "
                    f"({len(AP10K_KEYPOINTS)}, 3) AP-10K keypoints."
                )

            # QuadPose returns (y_norm, x_norm, confidence). PoseResult uses
            # source-frame pixel coordinates in (x, y, confidence) order.
            converted = np.empty_like(predicted, dtype=np.float32)
            converted[:, 0] = predicted[:, 1] * frame.width
            converted[:, 1] = predicted[:, 0] * frame.height
            converted[:, 2] = predicted[:, 2]
            valid = (
                np.isfinite(converted).all(axis=1)
                & (converted[:, 2] >= KEYPOINT_MIN_SCORE)
                & (converted[:, 0] >= 0.0)
                & (converted[:, 0] < frame.width)
                & (converted[:, 1] >= 0.0)
                & (converted[:, 1] < frame.height)
            )
            converted[~valid, :2] = np.nan
            converted[~valid, 2] = 0.0
            keypoints[index] = converted


def _revision(model_id: str) -> str | None:
    """Commit hash of a cached snapshot, or None when it was not recorded."""

    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return None
    resolved = try_to_load_from_cache(model_id, "config.json")
    if not isinstance(resolved, str):
        return None
    # .../snapshots/<revision>/config.json
    parts = Path(resolved).parts
    if "snapshots" not in parts:
        return None
    return parts[parts.index("snapshots") + 1]


# Preserve the old import name for callers that only depended on the interface.
VitPoseAp10kBackend = QuadPoseBackend

_BACKEND: QuadPoseBackend | None = None


def get_pose_backend() -> QuadPoseBackend:
    """Return the process-wide backend. Weights load on the first ``process``."""

    global _BACKEND
    if _BACKEND is None:
        _BACKEND = QuadPoseBackend()
    return _BACKEND
