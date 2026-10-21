"""Tests for the raw measurement helpers."""

import unittest

import numpy as np

from gait_engine.features import (
    MOTION_FLOOR,
    hip_stability,
    motion_statistics,
    movement_consistency,
)
from gait_engine.metrics import compute_gait_metrics


def build_keypoints(frames, *, hip_offsets=None, confidence=0.9):
    """Build a (frames, 17, 3) AP-10K array of (y, x, confidence)."""

    from gait_engine.quadruped import L_HIP_INDEX, R_HIP_INDEX

    keypoints = np.zeros((frames, 17, 3), dtype=np.float32)
    keypoints[:, :, 2] = confidence
    for index in range(frames):
        offset = 0.0 if hip_offsets is None else hip_offsets[index]
        keypoints[index, L_HIP_INDEX, 0] = 0.5 + offset
        keypoints[index, R_HIP_INDEX, 0] = 0.5 + offset
    return keypoints


class MotionStatisticsTests(unittest.TestCase):
    def test_empty_signal_is_all_zero(self):
        self.assertEqual(motion_statistics([]), (0.0, 0.0, 0.0))

    def test_steady_signal_has_no_deviation(self):
        mean, deviation, coverage = motion_statistics([0.02, 0.02, 0.02])
        self.assertAlmostEqual(mean, 0.02)
        self.assertEqual(deviation, 0.0)
        self.assertEqual(coverage, 1.0)

    def test_coverage_counts_only_frames_above_the_motion_floor(self):
        still = MOTION_FLOOR / 2
        _, _, coverage = motion_statistics([0.02, still, 0.02, still])
        self.assertEqual(coverage, 0.5)


class MovementConsistencyTests(unittest.TestCase):
    def test_a_still_clip_is_not_scored(self):
        self.assertIsNone(movement_consistency(MOTION_FLOOR / 2, 0.0))

    def test_steady_movement_scores_one(self):
        self.assertEqual(movement_consistency(0.02, 0.0), 1.0)

    def test_erratic_movement_scores_lower_than_steady_movement(self):
        steady = movement_consistency(0.02, 0.002)
        erratic = movement_consistency(0.02, 0.010)
        self.assertGreater(steady, erratic)

    def test_score_never_goes_below_zero(self):
        self.assertEqual(movement_consistency(0.01, 0.5), 0.0)


class HipStabilityTests(unittest.TestCase):
    def test_too_few_confident_frames_is_not_scored(self):
        self.assertIsNone(hip_stability(build_keypoints(2)))

    def test_low_confidence_frames_are_ignored(self):
        self.assertIsNone(hip_stability(build_keypoints(10, confidence=0.05)))

    def test_a_level_hip_line_is_fully_stable(self):
        self.assertEqual(hip_stability(build_keypoints(10)), 1.0)

    def test_wobble_reduces_stability(self):
        offsets = [0.0, 0.03, -0.03, 0.03, -0.03, 0.0, 0.02, -0.02, 0.01, -0.01]
        wobbly = hip_stability(build_keypoints(10, hip_offsets=offsets))
        self.assertIsNotNone(wobbly)
        self.assertLess(wobbly, 1.0)


class GaitSymmetryTests(unittest.TestCase):
    """Stride uses AP-10K back paws, not a human ankle index."""

    def _blank(self):
        keypoints = np.zeros((6, 17, 3), dtype=np.float32)
        keypoints[:, :, 2] = 0.9
        return keypoints

    def test_identical_hind_paws_are_symmetric(self):
        from gait_engine.quadruped import L_HIND_PAW_INDEX, R_HIND_PAW_INDEX

        keypoints = self._blank()
        motion = [0.0, 0.1, 0.2, 0.1, 0.0, 0.1]
        keypoints[:, L_HIND_PAW_INDEX, 0] = motion
        keypoints[:, R_HIND_PAW_INDEX, 0] = motion

        metrics = compute_gait_metrics(keypoints)

        self.assertEqual(metrics.hind.symmetry_score, 1.0)
        self.assertEqual(metrics.hind.asymmetry_percent, 0.0)

    def test_a_still_pet_is_reported_as_unavailable_not_perfect(self):
        metrics = compute_gait_metrics(self._blank())

        self.assertIsNone(metrics.hind.symmetry_score)
        self.assertIsNone(metrics.hind.asymmetry_percent)

    def test_one_sided_hind_paw_motion_is_reported_as_asymmetric(self):
        from gait_engine.quadruped import L_HIND_PAW_INDEX

        keypoints = self._blank()
        keypoints[:, L_HIND_PAW_INDEX, 0] = [0.0, 0.1, 0.2, 0.1, 0.0, 0.1]

        metrics = compute_gait_metrics(keypoints)

        self.assertEqual(metrics.hind.symmetry_score, 0.0)
        self.assertEqual(metrics.hind.asymmetry_percent, 100.0)

    def test_knee_motion_is_not_reported_as_hind_paw_stride(self):
        from gait_engine.quadruped import KEYPOINT_NAMES

        keypoints = self._blank()
        motion = [0.0, 0.1, 0.2, 0.1, 0.0, 0.1]
        keypoints[:, KEYPOINT_NAMES.index("L_Knee"), 0] = motion
        keypoints[:, KEYPOINT_NAMES.index("R_Knee"), 0] = motion

        metrics = compute_gait_metrics(keypoints)

        self.assertIsNone(metrics.hind.symmetry_score)
        self.assertEqual(metrics.hind.left_motion, 0.0)
        self.assertEqual(metrics.hind.right_motion, 0.0)


if __name__ == "__main__":
    unittest.main()
