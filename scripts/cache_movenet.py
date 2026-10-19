#!/usr/bin/env python3
"""Download MoveNet Thunder into the local cache.

Run this at build or deploy time, before the API serves traffic, so the first
analysis request does not download the weights:

    python scripts/cache_movenet.py

Requires Python 3.10 or 3.11 and the pinned packages in requirements.txt.
TensorFlow does not support Python 3.12. If TensorFlow is not installed, the
API still analyzes clips with the OpenCV motion fallback and does not pretend
to have run MoveNet.

The cache directory is models/tfhub, or SILVERPAWS_MOVENET_CACHE when that
variable is set. load_movenet() points TFHUB_CACHE_DIR at the same place.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> int:
    from gait_engine.movenet import DEFAULT_MODEL_URL, cache_directory, load_movenet

    destination = cache_directory()
    print(f"Caching {DEFAULT_MODEL_URL}")
    print(f"Directory: {destination}")
    try:
        load_movenet(DEFAULT_MODEL_URL)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("MoveNet Thunder is cached. Later requests reuse this directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
