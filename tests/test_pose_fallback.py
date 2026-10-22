"""Pose failures stay on the OpenCV path and still return a result."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from gait_engine.pipeline import analyze_clip
from gait_engine.pose_backend import (
    AP10K_SWAP_PAIRS,
    choose_initial_dog,
    crop_from_keypoints,
    swap_left_right,
)
from gait_engine.sampling import apply_rotation


def write_clip(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240))
    if not writer.isOpened():
        raise unittest.SkipTest("OpenCV could not open a test video writer")
    for index in range(8):
        frame = np.full((240, 320, 3), 30, dtype=np.uint8)
        origin = 10 + index * 8
        cv2.rectangle(frame, (origin, 40), (origin + 60, 180), (220, 220, 220), -1)
        writer.write(frame)
    writer.release()


class PoseFallbackTests(unittest.TestCase):
    def test_a_pose_exception_keeps_the_motion_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path)

            class Broken:
                def process(self, frames):
                    raise RuntimeError("weights missing")

            with patch("gait_engine.pose_backend.get_pose_backend", return_value=Broken()):
                result = analyze_clip(path, use_pose=True)

        self.assertEqual(result["pipeline"], "opencv-motion")
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["diagnostics"]["poseSkipReason"])
        self.assertIn("RuntimeError", result["diagnostics"]["poseSkipReason"])
        self.assertIsNone(result["measurements"]["strideSymmetry"])


class PoseGeometryTests(unittest.TestCase):
    def test_the_first_dog_is_the_largest_then_the_most_central(self):
        boxes = [(0, 0, 10, 10), (100, 100, 40, 40), (140, 100, 40, 10)]
        self.assertEqual(choose_initial_dog(boxes, 200, 200), (100, 100, 40, 40))

    def test_a_keypoint_crop_grows_by_a_quarter(self):
        points = np.zeros((17, 3), dtype=np.float32)
        points[3, 2] = 0.9
        points[4, 2] = 0.9
        points[3, :2] = (40, 40)
        points[4, :2] = (80, 40)
        box = crop_from_keypoints(points, 200, 100)
        self.assertIsNotNone(box)
        assert box is not None
        self.assertAlmostEqual(box[0], 30.0)
        self.assertAlmostEqual(box[2], 60.0)

    def test_left_right_pairs_exchange(self):
        points = np.zeros((1, 17, 3), dtype=np.float32)
        for left, right in AP10K_SWAP_PAIRS:
            points[0, left, 0] = left
            points[0, right, 0] = right
        swapped = swap_left_right(points)
        for left, right in AP10K_SWAP_PAIRS:
            self.assertEqual(swapped[0, left, 0], right)
            self.assertEqual(swapped[0, right, 0], left)

    def test_rotation_turns_a_wide_frame_tall(self):
        frame = np.zeros((10, 20, 3), dtype=np.uint8)
        turned = apply_rotation(frame, 90)
        self.assertEqual(turned.shape[:2], (20, 10))


if __name__ == "__main__":
    unittest.main()
