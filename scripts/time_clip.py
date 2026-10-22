#!/usr/bin/env python3
"""Print per-stage seconds and peak RSS for one clip. Does not invent numbers."""

from __future__ import annotations

import resource
import sys
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def rss_mb() -> float:
    # Linux reports ru_maxrss in kilobytes.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> int:
    video = Path(sys.argv[1])
    from gait_engine.gait import compute_gait_metrics
    from gait_engine.pose_backend import get_pose_backend
    from gait_engine.sampling import sample_video

    started = time.perf_counter()
    sample_started = time.perf_counter()
    frames = sample_video(video)
    sample_seconds = time.perf_counter() - sample_started
    pose_started = time.perf_counter()
    result = get_pose_backend().process(frames)
    pose_seconds = time.perf_counter() - pose_started
    gait_started = time.perf_counter()
    compute_gait_metrics(
        result.keypoints,
        timestamps=result.timestamps_seconds,
        boxes=result.boxes,
        dog_frames_share=result.dog_frames_share,
    )
    gait_seconds = time.perf_counter() - gait_started
    total = time.perf_counter() - started
    print(f"frames {len(frames)}")
    print(f"sample_seconds {sample_seconds:.3f}")
    print(f"pose_seconds {pose_seconds:.3f}")
    print(f"gait_seconds {gait_seconds:.3f}")
    print(f"total_seconds {total:.3f}")
    print(f"peak_rss_mb {rss_mb():.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
