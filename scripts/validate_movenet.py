#!/usr/bin/env python3
"""Run the standalone MoveNet Thunder validation on a walking video.

Example:
    python scripts/validate_movenet.py path/to/walking_video.mp4

Colab:
    !python scripts/validate_movenet.py /content/walking_video.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract MoveNet Thunder keypoints and calculate ankle symmetry."
    )
    parser.add_argument("video", type=Path, help="Path to an MP4/MOV/AVI walking video.")
    parser.add_argument(
        "--model-url",
        default="https://tfhub.dev/google/movenet/singlepose/thunder/4",
        help="TensorFlow Hub URL for the MoveNet model.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.2,
        help="Hide keypoints below this confidence threshold (default: 0.2).",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional frame limit for a quick smoke test.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path for saving the full keypoints and metric summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Imports happen after argument parsing so --help works without ML packages.
    try:
        import numpy as np

        from gait_engine.movenet import (
            KEYPOINT_NAMES,
            extract_keypoints_from_video,
            load_movenet,
        )

        print(f"Loading MoveNet Thunder from {args.model_url} ...")
        model = load_movenet(args.model_url)
        print(f"Reading video: {args.video}")
        keypoints, fps = extract_keypoints_from_video(
            args.video,
            model,
            min_confidence=args.min_confidence,
            max_frames=args.max_frames,
        )
        # This script checks the human model only. Dog clips use
        # gait_engine.quadruped and do not read these ankle indexes.
        left_index = KEYPOINT_NAMES.index("left_ankle")
        right_index = KEYPOINT_NAMES.index("right_ankle")
        confidence = keypoints[:, :, 2]
        left_y = keypoints[:, left_index, 0].copy()
        right_y = keypoints[:, right_index, 0].copy()
        left_y[confidence[:, left_index] < args.min_confidence] = np.nan
        right_y[confidence[:, right_index] < args.min_confidence] = np.nan

        def _energy(values: np.ndarray) -> tuple[float, int]:
            valid = np.isfinite(values)
            count = int(np.count_nonzero(valid))
            adjacent = valid[:-1] & valid[1:]
            if count < 2 or not np.any(adjacent):
                return 0.0, count
            return float(np.sum(np.abs(np.diff(values))[adjacent])), count

        left_motion, valid_left = _energy(left_y)
        right_motion, valid_right = _energy(right_y)
        total_motion = left_motion + right_motion
        if valid_left < 2 or valid_right < 2 or total_motion == 0.0:
            symmetry_score = None
            asymmetry_percent = None
        else:
            symmetry_score = float(
                np.clip(1.0 - abs(left_motion - right_motion) / total_motion, 0.0, 1.0)
            )
            asymmetry_percent = round((1.0 - symmetry_score) * 100.0, 3)
        metrics = {
            "frame_count": int(keypoints.shape[0]),
            "valid_left_ankle_frames": valid_left,
            "valid_right_ankle_frames": valid_right,
            "left_ankle_motion": round(left_motion, 6),
            "right_ankle_motion": round(right_motion, 6),
            "stride_symmetry_score": None if symmetry_score is None else round(symmetry_score, 6),
            "asymmetry_percent": asymmetry_percent,
        }
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print("\nMoveNet validation complete")
    print("This human-pose check is not the dog measurement path.")
    print(f"Frames analyzed: {metrics['frame_count']}")
    print(f"Video FPS: {fps:.2f}")
    print(f"Keypoint tensor shape: {list(keypoints.shape)}")
    print("\nFirst-frame keypoints (normalized y, x, confidence):")
    for name, point in zip(KEYPOINT_NAMES, keypoints[0]):
        y, x, confidence = point
        print(f"  {name:14} y={y:.4f} x={x:.4f} confidence={confidence:.4f}")

    print("\nBasic gait metric")
    if metrics["stride_symmetry_score"] is None:
        print("  stride symmetry score: unavailable (not enough confident ankle motion)")
        print("  asymmetry estimate:    unavailable")
    else:
        print(
            "  stride symmetry score: "
            f"{metrics['stride_symmetry_score']:.3f} (1.0 is most symmetric)"
        )
        print(f"  asymmetry estimate:    {metrics['asymmetry_percent']:.2f}%")
    print(
        "  note: this is an experimental pipeline metric, not a medical diagnosis."
    )

    if args.output_json:
        output = {
            "video": str(args.video),
            "model_url": args.model_url,
            "fps": fps,
            "keypoint_names": list(KEYPOINT_NAMES),
            "keypoints": keypoints.tolist(),
            "metrics": metrics,
        }
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(f"\nSaved JSON output to: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
