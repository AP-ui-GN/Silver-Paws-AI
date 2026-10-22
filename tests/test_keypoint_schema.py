"""Keypoint schema and coordinate conversion tests for the AP-10K pose adapter."""

import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np

from gait_engine.pose_backend import (
    AP10K_KEYPOINTS,
    AP10K_SKELETON_EDGES,
    COCO17_EDGES,
    COCO17_KEYPOINTS,
    KEYPOINT_MIN_SCORE,
    MODEL_OUTPUT_EDGES,
    MODEL_OUTPUT_KEYPOINTS,
    MODEL_OUTPUT_SCHEMA,
    QuadPoseBackend,
    denormalize_from_box,
    dog_boxes_from_detections,
    normalize_to_box,
)


class SchemaTests(unittest.TestCase):
    def test_current_model_output_uses_the_pinned_ap10k_order(self):
        self.assertEqual(MODEL_OUTPUT_SCHEMA, "ap10k")
        self.assertEqual(MODEL_OUTPUT_KEYPOINTS, AP10K_KEYPOINTS)
        self.assertEqual(MODEL_OUTPUT_EDGES, AP10K_SKELETON_EDGES)
        self.assertEqual(len(AP10K_KEYPOINTS), 17)
        self.assertEqual(len(set(AP10K_KEYPOINTS)), 17)
        self.assertEqual(AP10K_KEYPOINTS[4], "root_of_tail")
        self.assertEqual(AP10K_KEYPOINTS[7], "left_front_paw")
        self.assertEqual(AP10K_KEYPOINTS[13], "left_back_paw")

    def test_legacy_coco_names_are_not_the_current_model_schema(self):
        self.assertEqual(len(COCO17_KEYPOINTS), 17)
        self.assertEqual(COCO17_KEYPOINTS[4], "right_ear")
        self.assertNotEqual(COCO17_KEYPOINTS, MODEL_OUTPUT_KEYPOINTS)
        self.assertNotEqual(COCO17_EDGES, MODEL_OUTPUT_EDGES)

    def test_every_ap10k_edge_uses_a_valid_keypoint_index(self):
        for start, end in AP10K_SKELETON_EDGES:
            self.assertIn(start, range(17))
            self.assertIn(end, range(17))


class CoordinateTests(unittest.TestCase):
    def test_box_normalization_round_trips(self):
        box = (408.1, 193.3, 551.8, 277.0)
        pixel = (495.6, 295.7)
        fraction = normalize_to_box(*pixel, box)
        self.assertGreaterEqual(fraction[0], 0.0)
        self.assertLessEqual(fraction[0], 1.0)
        self.assertGreaterEqual(fraction[1], 0.0)
        self.assertLessEqual(fraction[1], 1.0)
        back = denormalize_from_box(*fraction, box)
        self.assertAlmostEqual(back[0], pixel[0], places=4)
        self.assertAlmostEqual(back[1], pixel[1], places=4)

    def test_synthetic_box_fractions_round_trip(self):
        box = (10.0, 20.0, 100.0, 50.0)
        self.assertEqual(normalize_to_box(10.0, 20.0, box), (0.0, 0.0))
        self.assertEqual(normalize_to_box(110.0, 70.0, box), (1.0, 1.0))
        self.assertEqual(denormalize_from_box(0.25, 0.5, box), (35.0, 45.0))

    def test_quadpose_y_x_output_is_converted_to_pixel_x_y(self):
        backend = QuadPoseBackend()
        backend._pose = object()
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        sampled_frame = SimpleNamespace(image_bgr=frame, width=200, height=100)
        predicted = np.zeros((17, 3), dtype=np.float32)
        predicted[:, 0] = 0.25  # y in normalized image coordinates
        predicted[:, 1] = 0.5   # x in normalized image coordinates
        predicted[:, 2] = 0.9
        predicted[1, 2] = KEYPOINT_MIN_SCORE - 0.01
        keypoints = np.full((1, 17, 3), np.nan, dtype=np.float32)
        keypoints[:, :, 2] = 0.0

        with patch("gait_engine.quadpose._predict_frame", return_value=predicted):
            backend._run_pose_batch(
                [sampled_frame],
                [(10.0, 10.0, 160.0, 80.0)],
                [0],
                keypoints,
            )

        self.assertAlmostEqual(float(keypoints[0, 0, 0]), 100.0)
        self.assertAlmostEqual(float(keypoints[0, 0, 1]), 25.0)
        self.assertAlmostEqual(float(keypoints[0, 0, 2]), 0.9)
        self.assertTrue(np.isnan(keypoints[0, 1, 0]))
        self.assertTrue(np.isnan(keypoints[0, 1, 1]))
        self.assertEqual(float(keypoints[0, 1, 2]), 0.0)


class SubjectTests(unittest.TestCase):
    def test_a_person_box_is_not_returned_as_the_dog(self):
        labels = [0, 16]
        scores = [0.9, 0.8]
        boxes = np.array([[0, 0, 40, 200], [100, 100, 300, 250]], dtype=np.float32)
        dogs, dog_count, saw_person = dog_boxes_from_detections(
            labels,
            scores,
            boxes,
            dog_id=16,
            person_id=0,
            threshold=0.3,
        )
        self.assertTrue(saw_person)
        self.assertEqual(dog_count, 1)
        self.assertEqual(len(dogs), 1)
        self.assertAlmostEqual(dogs[0][0], 100.0)

    def test_a_person_box_alone_is_not_a_dog(self):
        dogs, dog_count, saw_person = dog_boxes_from_detections(
            [0],
            [0.99],
            np.array([[0, 0, 40, 200]], dtype=np.float32),
            dog_id=16,
            person_id=0,
            threshold=0.3,
        )
        self.assertEqual(dogs, [])
        self.assertEqual(dog_count, 0)
        self.assertTrue(saw_person)


if __name__ == "__main__":
    unittest.main()
