"""Model-independent tests for the QuadPose adapter and asset contract."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from gait_engine import quadpose


class _Input:
    name = "input"


class _FakeSession:
    def __init__(self, heatmap: np.ndarray | None = None):
        self.heatmap = heatmap
        self.calls = 0

    def get_inputs(self):
        return [_Input()]

    def get_outputs(self):
        return [SimpleNamespace(name="heatmap")]

    def run(self, _outputs, _inputs):
        self.calls += 1
        assert self.heatmap is not None
        return [self.heatmap]


class QuadPoseCropTests(unittest.TestCase):
    def test_crop_rejects_nonfinite_or_degenerate_dog_boxes(self):
        for box in (
            np.array([0.0, 0.0, 0.0, 20.0]),
            np.array([0.0, 0.0, 20.0, 0.0]),
            np.array([0.0, np.nan, 20.0, 30.0]),
            np.array([0.0, 0.0, np.inf, 30.0]),
            np.array([1.0, 2.0, 3.0]),
        ):
            with self.subTest(box=box), self.assertRaises(ValueError):
                quadpose._compute_crop(box)

    def test_predict_frame_uses_the_selected_dog_box_and_returns_y_x_confidence(self):
        heatmap = np.zeros((1, 17, 64, 64), dtype=np.float32)
        heatmap[:, :, 32, 32] = 0.9
        session = _FakeSession(heatmap)
        frame = np.zeros((240, 320, 3), dtype=np.uint8)

        result = quadpose._predict_frame(
            session,
            frame,
            np.asarray([50.0, 30.0, 250.0, 210.0], dtype=np.float64),
        )

        self.assertEqual(result.shape, (17, 3))
        self.assertTrue(np.isfinite(result).all())
        self.assertTrue(np.all((result[:, :2] >= 0.0) & (result[:, :2] <= 1.0)))
        self.assertTrue(np.all(result[:, 2] >= 0.3))
        # The output contract is (y, x, confidence), normalized to source frame.
        self.assertAlmostEqual(float(result[0, 0]), 0.5, delta=0.03)
        self.assertAlmostEqual(float(result[0, 1]), 0.46875, delta=0.03)
        self.assertEqual(session.calls, 1)

    def test_wrong_onnx_output_shape_is_rejected(self):
        session = _FakeSession(np.zeros((1, 16, 64, 64), dtype=np.float32))
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "Unexpected QuadPose heatmap shape"):
            quadpose._predict_frame(
                session,
                frame,
                np.asarray([50.0, 30.0, 250.0, 210.0], dtype=np.float64),
            )


class QuadPoseCacheTests(unittest.TestCase):
    def setUp(self):
        quadpose._SESSION = None

    def tearDown(self):
        quadpose._SESSION = None

    def test_inference_does_not_download_when_checkpoint_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / quadpose.CHECKPOINT_FILENAME
            fake_onnxruntime = SimpleNamespace(InferenceSession=Mock())
            with patch.dict(sys.modules, {"onnxruntime": fake_onnxruntime}), patch(
                "gait_engine.quadpose.cache_path", return_value=missing
            ), patch("gait_engine.quadpose.ensure_checkpoint", side_effect=AssertionError("unexpected download")):
                with self.assertRaisesRegex(RuntimeError, "Run 'python scripts/cache_models.py'"):
                    quadpose.load_quadpose()

            fake_onnxruntime.InferenceSession.assert_not_called()

    def test_inference_rejects_a_checkpoint_with_wrong_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / quadpose.CHECKPOINT_FILENAME
            path.write_bytes(b"not-the-pinned-model")
            fake_onnxruntime = SimpleNamespace(InferenceSession=Mock())
            with patch.dict(sys.modules, {"onnxruntime": fake_onnxruntime}), patch(
                "gait_engine.quadpose.cache_path", return_value=path
            ), patch("gait_engine.quadpose._sha256", return_value="wrong-hash"):
                with self.assertRaisesRegex(RuntimeError, "checksum mismatch"):
                    quadpose.load_quadpose()
            fake_onnxruntime.InferenceSession.assert_not_called()

    def test_only_valid_cached_hash_is_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / quadpose.CHECKPOINT_FILENAME
            path.write_bytes(b"unit-test-placeholder")
            session = _FakeSession(np.zeros((1, 17, 64, 64), dtype=np.float32))
            fake_onnxruntime = SimpleNamespace(InferenceSession=Mock(return_value=session))
            with patch.dict(sys.modules, {"onnxruntime": fake_onnxruntime}), patch(
                "gait_engine.quadpose.cache_path", return_value=path
            ), patch(
                "gait_engine.quadpose._sha256", return_value=quadpose.CHECKPOINT_SHA256
            ):
                loaded = quadpose.load_quadpose()

            self.assertIs(loaded, session)
            fake_onnxruntime.InferenceSession.assert_called_once_with(
                str(path), providers=["CPUExecutionProvider"]
            )


if __name__ == "__main__":
    unittest.main()
