"""The loaded pose head is COCO-17. AP-10K names are a different index order."""

import unittest

import numpy as np

from gait_engine.pose_backend import (
    AP10K_KEYPOINTS,
    COCO17_EDGES,
    COCO17_KEYPOINTS,
    MODEL_OUTPUT_EDGES,
    MODEL_OUTPUT_KEYPOINTS,
    MODEL_OUTPUT_SCHEMA,
    denormalize_from_box,
    dog_boxes_from_detections,
    normalize_to_box,
)

# First frame of the side-view clip, dataset_index 3, dog box only.
# These are the raw decoder channels, not AP-10K names.
SIDE_VIEW_FRAME = np.array(
    [
        [420.0, 341.5],
        [443.5, 317.0],
        [432.0, 318.5],
        [501.3, 297.5],
        [495.6, 295.7],
        [618.3, 279.2],
        [590.3, 284.9],
        [613.9, 402.8],
        [607.9, 367.9],
        [597.9, 448.2],
        [624.5, 400.3],
        [838.7, 270.0],
        [797.2, 309.1],
        [812.5, 338.3],
        [846.9, 387.2],
        [862.1, 440.8],
        [855.3, 438.5],
    ],
    dtype=np.float32,
)


def _distance(a: int, b: int) -> float:
    return float(np.linalg.norm(SIDE_VIEW_FRAME[a] - SIDE_VIEW_FRAME[b]))


class SchemaTests(unittest.TestCase):
    def test_checkpoint_order_matches_the_coco_head(self):
        self.assertEqual(MODEL_OUTPUT_SCHEMA, "coco-17")
        self.assertEqual(MODEL_OUTPUT_KEYPOINTS, COCO17_KEYPOINTS)
        self.assertEqual(MODEL_OUTPUT_EDGES, COCO17_EDGES)
        self.assertEqual(COCO17_KEYPOINTS[0], "nose")
        self.assertEqual(COCO17_KEYPOINTS[4], "right_ear")
        self.assertEqual(AP10K_KEYPOINTS[4], "root_of_tail")
        self.assertNotEqual(COCO17_KEYPOINTS[4], AP10K_KEYPOINTS[4])

    def test_every_coco_index_has_one_name(self):
        self.assertEqual(len(COCO17_KEYPOINTS), 17)
        self.assertEqual(len(set(COCO17_KEYPOINTS)), 17)
        for start, end in COCO17_EDGES:
            self.assertIn(start, range(17))
            self.assertIn(end, range(17))

    def test_channel_4_on_the_side_view_frame_is_a_head_point(self):
        # Index 4 sits next to the nose and far from the hip. Calling it the
        # base of the tail is what put root_of_tail on the head.
        ear_to_nose = _distance(4, 0)
        ear_to_hip = _distance(4, 11)
        self.assertLess(ear_to_nose, ear_to_hip)
        self.assertLess(ear_to_nose, 100.0)
        self.assertGreater(ear_to_hip, 300.0)


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


if __name__ == "__main__":
    unittest.main()
