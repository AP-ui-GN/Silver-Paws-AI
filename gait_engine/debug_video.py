"""Draw a debug clip for the command line. The API does not call this."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .gait import foot_strike_frames
from .pose_backend import (
    AP10K_KEYPOINTS,
    AP10K_SKELETON_EDGES,
    KEYPOINT_MIN_SCORE,
    get_pose_backend,
)
from .sampling import sample_video

PAW_NAMES = {
    "frontLeft": "left_front_paw",
    "frontRight": "right_front_paw",
    "rearLeft": "left_back_paw",
    "rearRight": "right_back_paw",
}


def write_debug_video(video_path: str | Path, output_path: str | Path) -> None:
    """Write skeleton, dog box, and stride-peak markers. Does not return video bytes."""

    frames = sample_video(video_path)
    if not frames:
        raise ValueError("No frames were sampled.")
    result = get_pose_backend().process(frames)
    strikes = foot_strike_frames(
        result.keypoints,
        timestamps=result.timestamps_seconds,
        boxes=result.boxes,
    )
    marked = {
        name: set(indexes)
        for name, indexes in strikes.items()
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    height, width = frames[0].image_bgr.shape[:2]
    writer = cv2.VideoWriter(
        str(output),
        cv2.VideoWriter_fourcc(*"mp4v"),
        15,
        (width, height),
    )
    if not writer.isOpened():
        raise ValueError(f"Could not write {output}")
    try:
        for index, frame in enumerate(frames):
            image = frame.image_bgr.copy()
            box = result.boxes[index]
            if box is not None:
                x, y, w, h = [int(round(value)) for value in box]
                cv2.rectangle(image, (x, y), (x + w, y + h), (40, 180, 60), 2)
            points = result.keypoints[index]
            for start, end in AP10K_SKELETON_EDGES:
                if points[start, 2] < KEYPOINT_MIN_SCORE or points[end, 2] < KEYPOINT_MIN_SCORE:
                    continue
                if not np.isfinite(points[start, 0]) or not np.isfinite(points[end, 0]):
                    continue
                p1 = (int(round(points[start, 0])), int(round(points[start, 1])))
                p2 = (int(round(points[end, 0])), int(round(points[end, 1])))
                cv2.line(image, p1, p2, (30, 90, 200), 2)
            for joint, point in enumerate(points):
                if point[2] < KEYPOINT_MIN_SCORE or not np.isfinite(point[0]):
                    continue
                center = (int(round(point[0])), int(round(point[1])))
                cv2.circle(image, center, 3, (20, 20, 20), -1)
            for paw_name, joint_name in PAW_NAMES.items():
                if index not in marked[paw_name]:
                    continue
                joint = AP10K_KEYPOINTS.index(joint_name)
                point = points[joint]
                if not np.isfinite(point[0]):
                    continue
                center = (int(round(point[0])), int(round(point[1])))
                cv2.circle(image, center, 8, (0, 0, 220), 2)
            writer.write(image)
    finally:
        writer.release()
