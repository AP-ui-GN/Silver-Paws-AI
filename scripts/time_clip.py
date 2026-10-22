#!/usr/bin/env python3
"""Print per-stage seconds and peak RSS for one clip. Does not invent numbers."""

from __future__ import annotations

import sys
import time

try:
    import resource as _resource
except ImportError:  # Windows does not provide the POSIX resource module.
    _resource = None
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def rss_mb() -> float | None:
    """Return peak RSS in MiB where the OS exposes it, otherwise None.

    Linux reports ru_maxrss in KiB; macOS reports bytes. Windows does not
    provide the POSIX resource module, so the benchmark still runs there but
    reports memory as unavailable.
    """
    if _resource is None:
        return None
    peak = _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024.0 * 1024.0) if sys.platform == "darwin" else peak / 1024.0


def _supports_ap10k_gait(keypoint_schema: str) -> bool:
    """Gait formulas index AP-10K landmarks and must not run on COCO-17."""
    return keypoint_schema == "ap10k"


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
    gait_seconds = None
    if _supports_ap10k_gait(result.keypoint_schema):
        gait_started = time.perf_counter()
        compute_gait_metrics(
            result.keypoints,
            timestamps=result.timestamps_seconds,
            boxes=result.boxes,
            dog_frames_share=result.dog_frames_share,
        )
        gait_seconds = time.perf_counter() - gait_started
    else:
        print(
            f"gait_metrics_skipped schema={result.keypoint_schema} requires=ap10k",
            file=sys.stderr,
        )
    total = time.perf_counter() - started
    print(f"frames {len(frames)}")
    print(f"sample_seconds {sample_seconds:.3f}")
    print(f"pose_seconds {pose_seconds:.3f}")
    print(
        f"gait_seconds {gait_seconds:.3f}"
        if gait_seconds is not None
        else "gait_seconds not_measured"
    )
    print(f"total_seconds {total:.3f}")
    peak_rss = rss_mb()
    print(f"peak_rss_mb {peak_rss:.1f}" if peak_rss is not None else "peak_rss_mb not_available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
