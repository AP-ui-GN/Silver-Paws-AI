"""The setup report inspects only local caches and never downloads model weights."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gait_engine.pose_backend import DETECTOR_ID
from gait_engine.quadpose import CHECKPOINT_FILENAME, CHECKPOINT_SHA256, MODEL_NAME, MODEL_VERSION
from gait_engine.setup_check import collect_setup, format_setup, inspect_model, inspect_quadpose


def _write_detector_snapshot(root: Path, *, weight: bool) -> None:
    folder = "models--" + DETECTOR_ID.replace("/", "--")
    snapshot = root / "hub" / folder / "snapshots" / "abc"
    snapshot.mkdir(parents=True)
    (snapshot / "config.json").write_text(json.dumps({"id2label": {"0": "dog"}}), encoding="utf8")
    if weight:
        (snapshot / "model.safetensors").write_bytes(b"test-fixture-not-real-weights")


class SetupCheckTests(unittest.TestCase):
    def test_an_empty_cache_reports_detector_and_pose_weights_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = collect_setup(root)
            detector = inspect_model(root, DETECTOR_ID)
            pose = inspect_quadpose(root)

        self.assertFalse(detector["weightsPresent"])
        self.assertFalse(detector["configPresent"])
        self.assertFalse(pose["weightsPresent"])
        self.assertFalse(pose["checksumValid"])
        self.assertEqual(pose["schema"], "absent")
        self.assertEqual(pose["modelId"], MODEL_NAME)
        self.assertEqual(pose["modelVersion"], MODEL_VERSION)
        self.assertFalse(report["poseReady"])
        self.assertFalse(report["downloadsWeights"])

    def test_nonempty_but_unverified_onnx_file_is_not_called_ap10k(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / CHECKPOINT_FILENAME).write_bytes(b"not-a-real-checkpoint")
            pose = inspect_quadpose(root)

        self.assertTrue(pose["weightsPresent"])
        self.assertFalse(pose["checksumValid"])
        self.assertEqual(pose["schema"], "unverified")
        self.assertIsNone(pose["channel4"])

    def test_only_a_matching_pinned_hash_enables_ap10k_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / CHECKPOINT_FILENAME).write_bytes(b"test-file; checksum mocked for this unit test")
            with patch("gait_engine.setup_check._sha256", return_value=CHECKPOINT_SHA256):
                pose = inspect_quadpose(root)

        self.assertTrue(pose["checksumValid"])
        self.assertEqual(pose["schema"], "ap10k")
        self.assertEqual(pose["channel4"], "Root of tail")

    def test_detector_cache_is_reported_separately_from_pose_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_detector_snapshot(root, weight=True)
            detector = inspect_model(root, DETECTOR_ID)
            pose = inspect_quadpose(root)

        self.assertTrue(detector["configPresent"])
        self.assertTrue(detector["weightsPresent"])
        self.assertFalse(pose["weightsPresent"])
        self.assertFalse(pose["checksumValid"])

    def test_setup_cli_json_is_valid_and_never_downloads_weights(self):
        repository_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            cache_root = Path(directory)
            hf_cache = cache_root / "hf"
            pose_cache = cache_root / "quadpose"
            hf_cache.mkdir()
            pose_cache.mkdir()
            environment = os.environ.copy()
            environment["HF_HOME"] = str(hf_cache)
            environment["SILVERPAWS_QUADPOSE_CACHE"] = str(pose_cache)
            completed = subprocess.run(
                [sys.executable, str(repository_root / "scripts" / "check_setup.py"), "--json"],
                cwd=repository_root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )

            report = json.loads(completed.stdout)
            self.assertFalse((pose_cache / CHECKPOINT_FILENAME).exists())

        self.assertFalse(report["downloadsWeights"])
        self.assertIn("fallbackReady", report)
        self.assertIn("poseReady", report)
        self.assertIn("onnxruntime", report["poseDependencies"])
        self.assertIn("detector", report)
        self.assertIn("pose", report)
        self.assertEqual(report["pose"]["schema"], "absent")
        self.assertIn("This command does not download weights.", format_setup(report))


if __name__ == "__main__":
    unittest.main()
