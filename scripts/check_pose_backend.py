#!/usr/bin/env python3
"""Draw dog boxes and AP-10K skeletons on eight frames of one clip.

    python scripts/check_pose_backend.py clip.mp4 --out outputs/pose-check/

Prints two sanity checks and does not claim the pose is validated:
the nose should sit farther from the root of the tail than either eye does,
and the back paws should sit below the hips in the image.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draw a dog pose check on eight frames.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/pose-check"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from gait_engine.pose_backend import (
        AP10K_KEYPOINTS,
        AP10K_SKELETON_EDGES,
        KEYPOINT_MIN_SCORE,
        LEFT_EYE,
        LEFT_BACK_PAW,
        LEFT_HIP,
        NOSE,
        RIGHT_EYE,
        RIGHT_BACK_PAW,
        RIGHT_HIP,
        ROOT_OF_TAIL,
        get_pose_backend,
    )
    from gait_engine.sampling import sample_video

    frames = sample_video(args.video)
    if not frames:
        print("No frames were sampled.", file=sys.stderr)
        return 2
    result = get_pose_backend().process(frames)
    args.out.mkdir(parents=True, exist_ok=True)

    step = max(1, len(frames) // 8)
    picked = list(range(0, len(frames), step))[:8]
    for slot, index in enumerate(picked):
        image = frames[index].image_bgr.copy()
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
        for name, point in zip(AP10K_KEYPOINTS, points):
            if point[2] < KEYPOINT_MIN_SCORE or not np.isfinite(point[0]):
                continue
            center = (int(round(point[0])), int(round(point[1])))
            cv2.circle(image, center, 3, (20, 20, 20), -1)
            cv2.putText(
                image,
                name,
                (center[0] + 4, center[1] - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
        cv2.imwrite(str(args.out / f"frame-{slot:02d}.jpg"), image)

    finite = np.isfinite(result.keypoints[:, :, 0])
    def median_point(index: int) -> np.ndarray | None:
        rows = result.keypoints[:, index, :]
        keep = finite[:, index] & (rows[:, 2] >= KEYPOINT_MIN_SCORE)
        if not np.any(keep):
            return None
        return np.median(rows[keep, :2], axis=0)

    nose = median_point(NOSE)
    tail = median_point(ROOT_OF_TAIL)
    left_eye = median_point(LEFT_EYE)
    right_eye = median_point(RIGHT_EYE)
    if nose is None or tail is None or left_eye is None or right_eye is None:
        print("Sanity: nose/eyes/tail were not all measured. Not scored.")
    else:
        nose_tail = float(np.linalg.norm(nose - tail))
        eye_tail = max(
            float(np.linalg.norm(left_eye - tail)),
            float(np.linalg.norm(right_eye - tail)),
        )
        print(
            f"Sanity: nose-to-tail {nose_tail:.1f}px, farther eye-to-tail {eye_tail:.1f}px, "
            f"nose farther={nose_tail > eye_tail}."
        )

    def below(paw: int, hip: int) -> str:
        paw_point = median_point(paw)
        hip_point = median_point(hip)
        if paw_point is None or hip_point is None:
            return "not measured"
        return "yes" if paw_point[1] > hip_point[1] else "no"

    print(f"Sanity: left back paw below hip: {below(LEFT_BACK_PAW, LEFT_HIP)}.")
    print(f"Sanity: right back paw below hip: {below(RIGHT_BACK_PAW, RIGHT_HIP)}.")
    print(f"dogFramesShare={result.dog_frames_share} multipleDogs={result.multiple_dogs} personPresent={result.person_present}")
    print(f"Wrote {len(picked)} frames to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
