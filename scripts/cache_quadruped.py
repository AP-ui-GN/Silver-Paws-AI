#!/usr/bin/env python3
"""Download the published RTMPose-m AP-10K ONNX file into the local cache.

    python scripts/cache_quadruped.py

The file lands in ``models/rtmpose`` unless ``SILVERPAWS_RTMPOSE_CACHE`` is
set. ``load_quadruped()`` reads that same path, so a warmed cache is reused
instead of downloading on the first request.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> int:
    from gait_engine.quadruped import MODEL_NAME, MODEL_VERSION, ensure_model_file

    path = ensure_model_file()
    print(f"Cached {MODEL_NAME} {MODEL_VERSION}")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
