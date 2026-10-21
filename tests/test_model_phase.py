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
from gait_engine.quadpose import MODEL_NAME, MODEL_VERSION, PIPELINE_ID


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
        array[0, 2, 1] = 1.2
        points = summarize_pose_coordinates(
            array,
            frame_threshold=0.3,
            keypoint_threshold=0.2,
        )
        self.assertNotIn("Nose", {point["name"] for point in points})

    def test_pose_coordinates_map_letterboxed_landmarks_to_source_frame(self):
        array = keypoints(1, 0.9)
        array[0, 0, :2] = (0.3, 0.5)
        points = summarize_pose_coordinates(
            array,
            frame_threshold=0.3,
            keypoint_threshold=0.2,
            frame_width=16,
            frame_height=9,
            undo_letterbox=True,
        )

        nose = next(point for point in points if point["name"] == "L_Eye")
        self.assertAlmostEqual(nose["x"], 0.5)
        self.assertAlmostEqual(nose["y"], (0.3 - 0.21875) / 0.5625, places=4)


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


class AiUseIdTests(unittest.TestCase):
    def test_a_pose_run_lists_pose_and_the_motion_measurement(self):
        ids = ai_use_ids("quadpose")

        self.assertEqual(
            ids,
            ["pose-model", "motion-fallback", "scoring", "observation-rules"],
        )
        self.assertNotIn("development", ids)
        self.assertNotIn("llm-rewrite", ids)


class QuadPoseResultTests(unittest.TestCase):
    def test_a_dog_model_run_reports_quadpose_and_not_movenet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "walk.avi"
            write_clip(path, frames=8)
            result = analyze_clip(path)

        self.assertIsNone(result["diagnostics"]["poseSkipReason"])
        self.assertEqual(result["pipeline"], PIPELINE_ID)
        self.assertEqual(result["modelInfo"]["pipeline"], PIPELINE_ID)
        self.assertEqual(result["modelInfo"]["modelName"], MODEL_NAME)
        self.assertEqual(result["modelInfo"]["modelVersion"], MODEL_VERSION)
        self.assertEqual(result["modelInfo"]["runsOn"], "server")
        self.assertNotEqual(result["pipeline"], "movenet")
        self.assertNotEqual(result["modelInfo"]["pipeline"], "movenet")
        self.assertNotIn("MoveNet", result["modelInfo"]["modelName"])
        self.assertNotIn("movenet", result["modelInfo"]["modelName"].lower())
        self.assertEqual(result["aiUse"][0], "pose-model")
        self.assertNotIn("human", result["limitations"].lower())
        for key in ("leftAnkleMotion", "rightAnkleMotion", "hipStability"):
            value = result["measurements"][key]
            self.assertTrue(value is None or isinstance(value, float))
        if result["lowConfidence"]:
            self.assertIsNone(result["measurements"]["leftAnkleMotion"])
            self.assertIsNone(result["measurements"]["rightAnkleMotion"])
            self.assertIsNone(result["measurements"]["hipStability"])
