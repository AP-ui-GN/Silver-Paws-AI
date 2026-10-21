"""Confidence gating, clip-quality notes, and model identity."""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from gait_engine.clip_quality import quality_notes
from gait_engine.confidence import (
    pose_is_trusted,
    summarize_keypoints,
    summarize_pose_coordinates,
)
from gait_engine.pipeline import MIN_POSE_CONFIDENCE, ai_use_ids, analyze_clip


def keypoints(frames, confidence):
    array = np.zeros((frames, 17, 3), dtype=np.float32)
    array[:, :, 2] = confidence
    array[:, 15, 0] = 0.4
    array[:, 16, 0] = 0.6
    return array


class ConfidenceSummaryTests(unittest.TestCase):
    def test_a_confident_clip_counts_every_frame(self):
        summary = summarize_keypoints(keypoints(8, 0.9), frame_threshold=0.3)

        self.assertEqual(summary["modelConfidence"], 0.9)
        self.assertEqual(summary["framesUsed"], 8)
        self.assertEqual(summary["framesTotal"], 8)
        self.assertTrue(pose_is_trusted(summary, minimum=MIN_POSE_CONFIDENCE))

    def test_low_confidence_is_not_trusted_and_is_not_reported_as_missing(self):
        summary = summarize_keypoints(keypoints(6, 0.1), frame_threshold=0.3)

        self.assertEqual(summary["modelConfidence"], 0.1)
        self.assertEqual(summary["framesUsed"], 0)
        self.assertEqual(summary["framesTotal"], 6)
        self.assertFalse(pose_is_trusted(summary, minimum=MIN_POSE_CONFIDENCE))

    def test_keypoints_with_no_finite_confidence_stay_unmeasured(self):
        array = np.full((4, 17, 3), np.nan, dtype=np.float32)
        summary = summarize_keypoints(array, frame_threshold=0.3)

        self.assertIsNone(summary["modelConfidence"])
        self.assertEqual(summary["framesUsed"], 0)
        self.assertEqual(summary["framesTotal"], 4)

    def test_pose_coordinates_average_confident_frames_only(self):
        array = keypoints(2, 0.9)
        array[0, 5, :2] = (0.2, 0.4)
        array[1, 5, :2] = (0.6, 0.8)
        array[:, 8, 2] = 0.1

        points = summarize_pose_coordinates(
            array,
            frame_threshold=0.3,
            keypoint_threshold=0.2,
        )

        left_shoulder = next(point for point in points if point["name"] == "L_Shoulder")
        self.assertEqual(left_shoulder, {
            "name": "L_Shoulder",
            "x": 0.6,
            "y": 0.4,
            "confidence": 0.9,
        })
        self.assertNotIn("R_Shoulder", {point["name"] for point in points})

    def test_pose_coordinates_omit_low_confidence_and_out_of_frame_points(self):
        array = keypoints(1, 0.1)
        self.assertEqual(
            summarize_pose_coordinates(
                array,
                frame_threshold=0.3,
                keypoint_threshold=0.2,
            ),
            [],
        )

        array = keypoints(1, 0.9)
        array[0, 0, 1] = 1.2
        points = summarize_pose_coordinates(
            array,
            frame_threshold=0.3,
            keypoint_threshold=0.2,
        )
        self.assertNotIn("L_Eye", {point["name"] for point in points})

    def test_pose_coordinates_keep_source_frame_positions_unless_letterbox_is_requested(self):
        array = keypoints(1, 0.9)
        array[0, 0, :2] = (0.3, 0.5)
        points = summarize_pose_coordinates(
            array,
            frame_threshold=0.3,
            keypoint_threshold=0.2,
            frame_width=16,
            frame_height=9,
        )

        eye = next(point for point in points if point["name"] == "L_Eye")
        self.assertAlmostEqual(eye["x"], 0.5)
        self.assertAlmostEqual(eye["y"], 0.3)

        corrected = summarize_pose_coordinates(
            array,
            frame_threshold=0.3,
            keypoint_threshold=0.2,
            frame_width=16,
            frame_height=9,
            correct_letterbox=True,
        )
        corrected_eye = next(point for point in corrected if point["name"] == "L_Eye")
        self.assertAlmostEqual(corrected_eye["x"], 0.5)
        self.assertAlmostEqual(corrected_eye["y"], (0.3 - 0.21875) / 0.5625, places=4)


class ClipQualityTests(unittest.TestCase):
    def base(self, **overrides):
        values = {
            "frames_read": 30,
            "fps": 10.0,
            "duration_seconds": 3.0,
            "width": 640,
            "height": 480,
            "brightness": 0.4,
            "motion_mean": 0.05,
            "motion_coverage": 1.0,
        }
        values.update(overrides)
        return quality_notes(**values)

    def test_a_usable_clip_has_no_notes(self):
        self.assertEqual(self.base(), [])

    def test_unknown_duration_is_not_described_as_zero_seconds(self):
        notes = self.base(fps=0.0, duration_seconds=0.0, frames_read=30)

        self.assertEqual(notes, [])
        self.assertFalse(any("0.0 seconds" in note for note in notes))

    def test_a_dark_small_clip_asks_for_a_side_on_view(self):
        notes = self.base(width=160, height=120, brightness=0.02)

        self.assertTrue(any("too dark" in note for note in notes))
        self.assertTrue(any("too small" in note for note in notes))
        self.assertTrue(all("Film from the side with the whole body in frame." in note for note in notes))
        for banned in ("diagnos", "arthritis", "pain", "injury"):
            self.assertFalse(any(banned in note.lower() for note in notes))


def write_clip(path: Path, *, frames=12, size=(320, 240), color=(30, 30, 30), moving=True):
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10,
        size,
    )
    if not writer.isOpened():
        raise unittest.SkipTest("OpenCV could not open a test video writer")
    for index in range(frames):
        frame = np.full((size[1], size[0], 3), color, dtype=np.uint8)
        if moving:
            origin = 10 + index * 8
            cv2.rectangle(frame, (origin, 30), (origin + 70, 180), (220, 220, 220), -1)
        writer.write(frame)
    writer.release()


class OpenCvResultTests(unittest.TestCase):
    def test_motion_fallback_names_its_model_and_does_not_invent_pose_confidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path)
            result = analyze_clip(path, use_pose=False)

        self.assertEqual(result["pipeline"], "opencv-motion")
        self.assertEqual(result["modelInfo"]["pipeline"], "opencv-motion")
        self.assertEqual(result["modelInfo"]["modelName"], "OpenCV frame difference")
        self.assertEqual(result["modelInfo"]["runsOn"], "server")
        self.assertIsNone(result["modelConfidence"])
        self.assertIsNone(result["framesUsed"])
        self.assertIsNone(result["framesTotal"])
        self.assertFalse(result["lowConfidence"])
        self.assertIsNone(result["measurements"]["strideSymmetry"])
        self.assertIsNone(result["measurements"]["hipStability"])
        self.assertIsNone(result["measurements"]["poseKeypoints"])
        self.assertTrue(result["modelInfo"]["modelVersion"])
        self.assertEqual(
            result["aiUse"],
            ["motion-fallback", "scoring", "observation-rules"],
        )
        self.assertNotIn("pose-model", result["aiUse"])
        self.assertNotIn("llm-rewrite", result["aiUse"])
        self.assertNotIn("development", result["aiUse"])


class QuadrupedPipelineTests(unittest.TestCase):
    def test_a_missing_pose_model_does_not_invent_limb_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path)

            from gait_engine import pipeline as pipeline_module

            original = pipeline_module._try_pose
            pipeline_module._try_pose = lambda *_args, **_kwargs: (
                None,
                "RuntimeError: pose model unavailable",
                None,
            )
            try:
                result = analyze_clip(path)
            finally:
                pipeline_module._try_pose = original

        self.assertEqual(result["pipeline"], "opencv-motion")
        self.assertNotIn("pose-model", result["aiUse"])
        self.assertIsNone(result["measurements"]["leftHindPawMotion"])
        self.assertIsNone(result["measurements"]["rightHindPawMotion"])
        self.assertIsNone(result["measurements"]["leftForePawMotion"])
        self.assertIsNone(result["measurements"]["rightForePawMotion"])
        self.assertIsNone(result["measurements"]["strideSymmetry"])
        self.assertIsNone(result["measurements"]["hipStability"])
        self.assertFalse(result["lowConfidence"])
        self.assertNotEqual(result["measurements"]["leftHindPawMotion"], 0)
        self.assertNotIn("MoveNet", result["limitations"])

    def test_low_confidence_pose_keeps_the_quadruped_label_and_skips_limbs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path)
            low = np.full((8, 17, 3), 0.05, dtype=np.float32)
            low[:, 13, 0] = 0.4
            low[:, 16, 0] = 0.8

            from gait_engine import pipeline as pipeline_module

            original = pipeline_module._try_pose
            pipeline_module._try_pose = lambda *_args, **_kwargs: (low, None, "rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206")
            try:
                result = analyze_clip(path)
            finally:
                pipeline_module._try_pose = original

        self.assertEqual(result["pipeline"], "rtmpose-ap10k")
        self.assertEqual(result["modelInfo"]["pipeline"], "rtmpose-ap10k")
        self.assertEqual(result["modelInfo"]["modelName"], "RTMPose-m")
        self.assertTrue(result["lowConfidence"])
        self.assertIsNone(result["measurements"]["leftHindPawMotion"])
        self.assertIsNone(result["measurements"]["rightHindPawMotion"])
        self.assertIsNone(result["measurements"]["strideSymmetry"])
        self.assertIsNone(result["factors"]["symmetry"])
        self.assertNotEqual(result["measurements"]["strideSymmetry"], 0)
        self.assertEqual(result["aiUse"][0], "pose-model")
        self.assertIn("veterinarian", result["limitations"].lower())
        self.assertNotIn("diagnos", result["observation"].lower())

    def test_confident_hind_paws_score_stride_from_those_keypoints(self):
        from gait_engine.quadruped import L_HIND_PAW_INDEX, R_HIND_PAW_INDEX

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path, frames=12)
            points = np.zeros((12, 17, 3), dtype=np.float32)
            points[:, :, 2] = 0.9
            points[:, L_HIND_PAW_INDEX, 0] = np.linspace(0.2, 0.8, 12)
            points[:, R_HIND_PAW_INDEX, 0] = np.linspace(0.2, 0.8, 12)
            points[:, 11, 0] = 0.4
            points[:, 14, 0] = 0.4

            from gait_engine import pipeline as pipeline_module

            original = pipeline_module._try_pose
            pipeline_module._try_pose = lambda *_args, **_kwargs: (
                points,
                None,
                "rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206",
            )
            try:
                result = analyze_clip(path)
            finally:
                pipeline_module._try_pose = original

        self.assertEqual(result["pipeline"], "rtmpose-ap10k")
        self.assertFalse(result["lowConfidence"])
        self.assertEqual(result["measurements"]["strideSymmetry"], 1.0)
        self.assertGreater(result["measurements"]["leftHindPawMotion"], 0)
        self.assertEqual(
            result["measurements"]["leftHindPawMotion"],
            result["measurements"]["rightHindPawMotion"],
        )
        names = {point["name"] for point in result["measurements"]["poseKeypoints"]}
        self.assertIn("L_B_Paw", names)
        self.assertIn("R_B_Paw", names)
        self.assertNotIn("left_ankle", names)
        self.assertNotIn("right_ankle", names)

    def test_a_generated_clip_uses_the_quadruped_pipeline_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path, frames=6)
            result = analyze_clip(path)

        self.assertEqual(
            result["pipeline"],
            "rtmpose-ap10k",
            result["diagnostics"].get("poseSkipReason"),
        )
        self.assertEqual(result["modelInfo"]["modelName"], "RTMPose-m")
        self.assertIn("ap10k", result["modelInfo"]["modelVersion"])
        self.assertEqual(result["aiUse"][0], "pose-model")
        self.assertNotIn("MoveNet", result["modelInfo"]["modelName"])
        if result["lowConfidence"]:
            self.assertIsNone(result["measurements"]["leftHindPawMotion"])
            self.assertIsNone(result["measurements"]["rightHindPawMotion"])
            self.assertIsNone(result["measurements"]["leftForePawMotion"])
            self.assertIsNone(result["measurements"]["rightForePawMotion"])
            self.assertIsNone(result["measurements"]["strideSymmetry"])
            self.assertIsNone(result["measurements"]["hipStability"])


class AiUseIdTests(unittest.TestCase):
    def test_a_pose_run_lists_pose_and_the_motion_measurement(self):
        ids = ai_use_ids("rtmpose-ap10k")

        self.assertEqual(
            ids,
            ["pose-model", "motion-fallback", "scoring", "observation-rules"],
        )
        self.assertNotIn("development", ids)
        self.assertNotIn("llm-rewrite", ids)
