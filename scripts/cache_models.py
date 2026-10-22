#!/usr/bin/env python3
"""Cache the RT-DETR dog detector and the pinned QuadPose F2 checkpoint.

    python scripts/cache_models.py

Detector assets are cached under HF_HOME. The ONNX checkpoint is stored under
models/quadpose, or SILVERPAWS_QUADPOSE_CACHE when configured. This is an
explicit setup/build action; inference never downloads weights implicitly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> int:
    from gait_engine.pose_backend import DETECTOR_ID, hf_home
    from gait_engine.quadpose import MODEL_NAME, MODEL_VERSION, ensure_checkpoint

    home = hf_home()
    home.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(home)
    try:
        from transformers import RTDetrForObjectDetection, RTDetrImageProcessor
    except ImportError as exc:
        print(f"torch or transformers is not installed: {exc}", file=sys.stderr)
        return 1

    print(f"Caching dog detector {DETECTOR_ID} in {home}")
    try:
        RTDetrImageProcessor.from_pretrained(DETECTOR_ID)
        RTDetrForObjectDetection.from_pretrained(DETECTOR_ID)
        path = ensure_checkpoint()
    except Exception as exc:  # noqa: BLE001 - setup command must report the cause
        print(f"Could not cache the full pose stack: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Cached {MODEL_NAME} {MODEL_VERSION}")
    print(path)
    print("Detector and QuadPose assets are ready. Inference will not download weights.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
