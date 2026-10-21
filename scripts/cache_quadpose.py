#!/usr/bin/env python3
"""Download the pinned QuadPose F2 checkpoint into the local cache.

Run this at build or deploy time, before the API serves traffic, so the first
analysis request does not download the weights:

    python scripts/cache_quadpose.py

The file is models/quadpose/quadpose_f2.onnx, or SILVERPAWS_QUADPOSE_CACHE
when that variable is set to a file or a directory. The download is checked
against the SHA-256 pinned in gait_engine/quadpose.py. A mismatch is an error.
The weights are not committed.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> int:
    from gait_engine.quadpose import CHECKPOINT_URL, ensure_checkpoint

    print(f"Caching {CHECKPOINT_URL}")
    try:
        destination = ensure_checkpoint()
    except Exception as exc:  # noqa: BLE001 - the script should print the reason
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"QuadPose F2 is cached at {destination}. Later requests reuse this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
