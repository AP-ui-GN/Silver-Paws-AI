"""Report the local analysis toolchain without downloading model weights.

The detector uses Hugging Face's local cache. QuadPose F2 is a pinned ONNX
checkpoint installed explicitly by scripts/cache_models.py. A checkpoint is
considered valid only when its SHA-256 matches the published, pinned value.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

from .pose_backend import DETECTOR_ID, hf_home
from .quadpose import (
    CHECKPOINT_FILENAME,
    CHECKPOINT_SHA256,
    MODEL_NAME,
    MODEL_VERSION,
    _sha256,
    cache_path,
)

WEIGHT_NAMES = ("model.safetensors", "pytorch_model.bin")


def _repo_dir(root: Path, model_id: str) -> Path:
    folder = "models--" + model_id.replace("/", "--")
    hub = root / "hub" / folder
    if hub.is_dir():
        return hub
    return root / folder


def _snapshots(repo: Path) -> list[Path]:
    snapshot_root = repo / "snapshots"
    if not snapshot_root.is_dir():
        return []
    return sorted(path for path in snapshot_root.iterdir() if path.is_dir())


def _ready_file(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def inspect_model(root: Path, model_id: str) -> dict[str, object]:
    """Inspect a cached Hugging Face model by checking config and weight files."""

    snapshots = _snapshots(_repo_dir(root, model_id))
    config_present = False
    weights_present = False
    for snapshot in snapshots:
        config_present = config_present or _ready_file(snapshot / "config.json")
        weights_present = weights_present or any(
            _ready_file(snapshot / name) for name in WEIGHT_NAMES
        )
    return {
        "modelId": model_id,
        "configPresent": config_present,
        "weightsPresent": weights_present,
    }


def inspect_quadpose(path: Path | None = None) -> dict[str, object]:
    """Inspect the ONNX cache. A non-empty file is not valid until its hash matches."""

    target = path if path is not None else cache_path()
    if target.is_dir():
        target = target / CHECKPOINT_FILENAME

    present = _ready_file(target)
    checksum_valid = False
    if present:
        try:
            checksum_valid = _sha256(target) == CHECKPOINT_SHA256
        except OSError:
            checksum_valid = False

    schema = "ap10k" if checksum_valid else ("unverified" if present else "absent")
    return {
        "modelId": MODEL_NAME,
        "modelVersion": MODEL_VERSION,
        "path": str(target),
        "configPresent": present,
        "weightsPresent": present,
        "checksumValid": checksum_valid,
        "schema": schema,
        "channel4": "Root of tail" if checksum_valid else None,
    }


def opencv_version() -> str | None:
    try:
        import cv2
    except ImportError:
        return None
    return str(cv2.__version__)


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def collect_setup(root: Path | None = None) -> dict[str, object]:
    """Return capabilities found locally. This function never downloads weights."""

    detector_cache = root if root is not None else hf_home()
    pose_path = (root / CHECKPOINT_FILENAME) if root is not None else cache_path()
    pose = inspect_quadpose(pose_path)
    detector = inspect_model(detector_cache, DETECTOR_ID)
    dependencies = {
        "torch": _has_module("torch"),
        "transformers": _has_module("transformers"),
        "onnxruntime": _has_module("onnxruntime"),
    }
    opencv = opencv_version()
    return {
        "python": sys.version.split()[0],
        "opencv": opencv,
        "pose": pose,
        "detector": detector,
        "poseDependencies": dependencies,
        "poseReady": (
            all(dependencies.values())
            and detector["weightsPresent"]
            and pose["checksumValid"]
            and pose["schema"] == "ap10k"
        ),
        "fallbackReady": opencv is not None,
        "downloadsWeights": False,
    }


def format_setup(report: dict[str, object]) -> str:
    pose = report["pose"]
    detector = report["detector"]
    dependencies = report["poseDependencies"]
    assert isinstance(pose, dict)
    assert isinstance(detector, dict)
    assert isinstance(dependencies, dict)
    opencv = report["opencv"] or "not importable"
    lines = [
        f"Python {report['python']}",
        f"OpenCV {opencv}",
        f"Pose model: {pose['modelId']} ({pose['modelVersion']})",
        f"Pose weights: {'checksum verified' if pose['checksumValid'] else ('present but unverified' if pose['weightsPresent'] else 'absent')}",
        f"Pose schema: {pose['schema']}",
        f"Pose channel 4: {pose['channel4'] if pose['channel4'] is not None else 'not verified'}",
        f"Dog detector: {'cached' if detector['weightsPresent'] else 'absent'} ({detector['modelId']})",
        f"Pose dependencies: {'present' if all(dependencies.values()) else 'incomplete'} (torch + transformers + onnxruntime)",
        f"Pose capability ready: {'yes' if report['poseReady'] else 'no'}",
        f"OpenCV fallback ready: {'yes' if report['fallbackReady'] else 'no'}",
        "This command does not download weights.",
    ]
    return "\n".join(lines) + "\n"
