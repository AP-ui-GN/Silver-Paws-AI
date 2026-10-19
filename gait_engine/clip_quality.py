"""Clip-quality pre-check.

These notes tell an owner how to film a clearer walk. They never name a
condition, and a missing measurement is not reported as zero.
"""

from __future__ import annotations

from .features import MOTION_FLOOR

# A handful of frames is not enough to describe a walk. Matches the pipeline.
MIN_COMPARABLE_FRAMES = 5

# A useful walk is about 5 to 15 seconds. The server still accepts up to 120.
MIN_DURATION_SECONDS = 2.0
LONG_CLIP_SECONDS = 120.0
USEFUL_WALK = "A useful walk is about 5 to 15 seconds."
SERVER_ACCEPTS = "The server accepts a longer clip, up to 120 seconds."

# Below this short side, limbs are too few pixels to trust.
MIN_SHORT_SIDE = 240

# Mean grayscale, 0-1, after the same blur the motion path uses.
DARK_BRIGHTNESS = 0.12
BLOWN_BRIGHTNESS = 0.92

# Share of frame pairs that should show movement before we call the clip quiet.
LOW_MOTION_COVERAGE = 0.2

SIDE_ON = "Film from the side with the whole body in frame."


def quality_notes(
    *,
    frames_read: int,
    fps: float,
    duration_seconds: float,
    width: int,
    height: int,
    brightness: float | None,
    motion_mean: float,
    motion_coverage: float,
) -> list[str]:
    """Return actionable filming notes. An empty list means no check tripped."""

    notes: list[str] = []
    duration_known = fps > 0 and duration_seconds > 0

    if frames_read < MIN_COMPARABLE_FRAMES or (
        duration_known and duration_seconds < MIN_DURATION_SECONDS
    ):
        if duration_known:
            notes.append(
                f"This clip is {duration_seconds} seconds long, which is too short to "
                f"compare steps. {USEFUL_WALK} {SERVER_ACCEPTS} {SIDE_ON}"
            )
        else:
            notes.append(
                "This clip did not include enough frames to compare steps. "
                f"{USEFUL_WALK} {SERVER_ACCEPTS} {SIDE_ON}"
            )
    elif duration_known and duration_seconds > LONG_CLIP_SECONDS:
        notes.append(
            f"This clip is {duration_seconds} seconds long, past the 120 second limit. "
            f"Only the opening is measured. {USEFUL_WALK} {SIDE_ON}"
        )

    if width > 0 and height > 0 and min(width, height) < MIN_SHORT_SIDE:
        notes.append(
            "This picture is too small to see the body clearly. Move closer. " + SIDE_ON
        )

    if brightness is not None and brightness < DARK_BRIGHTNESS:
        notes.append(
            "This clip is too dark to see the body. Film in even light. " + SIDE_ON
        )
    elif brightness is not None and brightness > BLOWN_BRIGHTNESS:
        notes.append(
            "This clip is washed out. Film in even daylight. " + SIDE_ON
        )

    if motion_mean < MOTION_FLOOR:
        notes.append(
            "Almost no movement was visible between frames. Walk your pet across the "
            f"frame. {SIDE_ON}"
        )
    elif motion_coverage < LOW_MOTION_COVERAGE:
        notes.append(
            "Only a little of the clip shows movement. Keep your pet walking across "
            f"the frame. {SIDE_ON}"
        )

    return notes
