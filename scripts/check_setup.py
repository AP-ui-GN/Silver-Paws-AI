#!/usr/bin/env python3
"""Report the local fallback, detector, and QuadPose readiness without downloads.

    python scripts/check_setup.py
    python scripts/check_setup.py --json

The setup check inspects local dependency/cache state. It does not download
weights or run pose inference. Missing pose weights are reported as an
unavailable optional capability; OpenCV fallback may still be ready.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local SilverPaws analysis setup without downloading weights.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write machine-readable JSON for readiness probes.",
    )
    args = parser.parse_args()

    from gait_engine.setup_check import collect_setup, format_setup

    report = collect_setup()
    if args.json:
        sys.stdout.write(json.dumps(report, separators=(",", ":")) + "\n")
        # The readiness probe needs to inspect the report even when OpenCV is
        # unavailable, so JSON mode uses the report's fallbackReady field.
        return 0
    sys.stdout.write(format_setup(report))
    if report["opencv"] is None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
