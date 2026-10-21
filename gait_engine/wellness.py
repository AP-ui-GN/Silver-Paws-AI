"""Turns raw measurements into factor scores, an overall indicator, and text.

The measurement keys used here are the same camelCase keys the API returns, so
one vocabulary runs from this module through the server to the UI.

This is a wellness/observation layer. It describes what was measured. It never
names a condition, and it never claims certainty.
"""

from __future__ import annotations

import math

from .features import movement_consistency

# Weight of each factor inside the overall indicator. Only factors that were
# actually scored take part; the remaining weights are renormalized. A factor
# without an entry here is never counted, so a new factor needs a new weight.
# The numbers are relative — they do not have to sum to 1.
#
# A planning note suggested mobility 0.40, cognitive 0.35, and happiness 0.25.
# This pipeline does not measure cognition or happiness, so those weights are
# not used. Copying them would score something the clip never produced.
# The original three weights are unchanged, which keeps a motion-only clip on
# the same overall score as before:
#   movementConsistency — how steady frame-to-frame motion was
#   symmetry — left/right balance, only when pose landmarks were reliable
#   activity — how much of the clip actually contained movement
# Mobility is weighted like activity: useful on a pose clip, never required.
# Historical change is lighter on purpose. One previous walk should nudge the
# indicator, not rewrite it. The point difference is already stated in the
# observation, and CONCERNING_DROP raises a veterinarian prompt on its own.
DEFAULT_WEIGHTS: dict[str, float] = {
    "movementConsistency": 0.45,
    "symmetry": 0.35,
    "activity": 0.20,
    "mobility": 0.20,
    "historicalChange": 0.10,
}

FACTOR_LABELS: dict[str, str] = {
    "movementConsistency": "movement consistency",
    "symmetry": "stride symmetry",
    "mobility": "mobility",
    "activity": "activity",
    "historicalChange": "change from baseline",
}

# An overall drop of at least this many points against the previous saved walk is
# worth raising with a veterinarian. Ten points is large enough to notice on a
# 0–100 scale and small enough that the app does not wait for a collapse.
# It is a prompt to ask, never a diagnosis. Kept after review.
CONCERNING_DROP = 10.0

# Measured left/right asymmetry (percent) that is worth raising, when the
# symmetry measurement was reliable enough to report. Twenty percent is a
# stride-symmetry score of 0.80. concerning_change() ignores this unless
# symmetryReliable is true, so a noisy pose cannot trigger the prompt.
# Kept after review.
CONCERNING_ASYMMETRY = 20.0


def _is_number(value: object) -> bool:
    """True for a finite int or float. Booleans and missing values are not numbers."""

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unit(value: object) -> float | None:
    """Clamp a measured 0-1 value, or return None when it was not measured."""

    if not _is_number(value):
        return None
    return max(0.0, min(1.0, float(value)))


def _to_score(value: float | None) -> float | None:
    """Convert a 0-1 measurement into a rounded 0-100 factor score."""

    if value is None:
        return None
    return round(max(0.0, min(1.0, value)) * 100, 1)


def mobility_factor(measurements: dict) -> float | None:
    """Score hip-point and hind-paw mobility from pose measurements, from 0 to 100.

    Uses hipStability, leftHindPawMotion, rightHindPawMotion, and strideSymmetry.
    Returns None when the pose was not reliable, or when stride symmetry or
    either hind paw was not measured. A missing value is left out of the
    average. It is never filled in as zero.

    Hind-paw motion is a raw energy, not a 0-1 quality score, and it depends on
    camera distance and clip length. Both sides must have been measured. Their
    balance is already stored as strideSymmetry, so that balance is not scored
    a second time. Hip-point stability is averaged with stride symmetry when it
    was measured, and omitted when it was not. Fore-paw motion is reported
    separately and is not folded into this score.
    """

    if not measurements.get("symmetryReliable"):
        return None

    symmetry = _unit(measurements.get("strideSymmetry"))
    left = measurements.get("leftHindPawMotion")
    right = measurements.get("rightHindPawMotion")
    if symmetry is None or not _is_number(left) or not _is_number(right):
        return None

    parts = [symmetry]
    hip = _unit(measurements.get("hipStability"))
    if hip is not None:
        parts.append(hip)

    return round(sum(parts) / len(parts) * 100, 1)


def historical_change_factor(
    overall: float | None,
    previous_overall: float | None,
) -> float | None:
    """Turn the change against the previous walk into a 0-100 factor.

    100 means this walk's overall score is at or above the previous one. Each
    point of drop removes one point, floored at 0. A first walk — either score
    missing — returns None. That is not a zero, and it is not averaged in.

    The pipeline passes the overall score from the other factors, then blends
    this result back in. The factor describes that comparison. It does not
    include itself.
    """

    if not _is_number(overall) or not _is_number(previous_overall):
        return None

    drop = float(previous_overall) - float(overall)
    if drop <= 0:
        return 100.0
    return round(max(0.0, 100.0 - drop), 1)


def score_factors(measurements: dict) -> dict[str, float | None]:
    """Score every factor from the raw measurements.

    A None value means the clip did not carry enough signal to score that factor.
    It never means zero.
    """

    symmetry = measurements.get("strideSymmetry")
    if not measurements.get("symmetryReliable"):
        symmetry = None

    consistency = movement_consistency(
        measurements.get("motionMean", 0.0),
        measurements.get("motionStd", 0.0),
    )

    return {
        "movementConsistency": _to_score(consistency),
        "symmetry": _to_score(symmetry),
        "mobility": mobility_factor(measurements),
        "activity": _to_score(measurements.get("motionCoverage")),
        "historicalChange": None,
    }


def overall_score(
    factors: dict[str, float | None],
    weights: dict[str, float] | None = None,
) -> float | None:
    """Blend the scored factors into one 0-100 indicator.

    Missing factors are skipped and the remaining weights are renormalized, so a
    clip that only supports two factors still gets an honest overall value.
    """

    weights = weights or DEFAULT_WEIGHTS
    total_weight = 0.0
    weighted_sum = 0.0

    for name, weight in weights.items():
        score = factors.get(name)
        if score is None:
            continue
        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0.0:
        return None

    return round(weighted_sum / total_weight, 1)


def weights_used(factors: dict[str, float | None]) -> dict[str, float]:
    """Report the weights that actually contributed, so the score is auditable."""

    contributing = {
        name: weight
        for name, weight in DEFAULT_WEIGHTS.items()
        if factors.get(name) is not None
    }
    total = sum(contributing.values())
    if total == 0.0:
        return {}
    return {name: round(weight / total, 4) for name, weight in contributing.items()}


def concerning_change(
    overall: float | None,
    previous_overall: float | None,
    measurements: dict,
) -> bool:
    """Decide whether this result is worth raising with a veterinarian."""

    if overall is not None and previous_overall is not None:
        if previous_overall - overall >= CONCERNING_DROP:
            return True

    asymmetry = measurements.get("asymmetryPercent")
    if measurements.get("symmetryReliable") and asymmetry is not None:
        if asymmetry >= CONCERNING_ASYMMETRY:
            return True

    return False


def lowest_scored_factor(factors: dict[str, float | None]) -> tuple[str, float] | None:
    """Return the (name, score) of the weakest scored factor, if any."""

    scored = [(name, score) for name, score in factors.items() if score is not None]
    if not scored:
        return None
    return min(scored, key=lambda pair: pair[1])


def build_observation(
    *,
    pet_name: str | None,
    measurements: dict,
    factors: dict[str, float | None],
    overall: float | None,
    previous_overall: float | None,
    signal_quality: str,
    signal_note: str,
    concerning: bool,
) -> str:
    """Write the rule-based observation text.

    Every number in this text comes from the measurements or factor scores above.
    This text is also the fallback whenever a model rewrite fails validation.
    """

    subject = (pet_name or "Your pet").strip() or "Your pet"
    sentences: list[str] = []

    if signal_quality == "unusable" or overall is None:
        sentences.append(
            f"SilverPaws could not measure enough movement in this clip to describe "
            f"{subject}'s walking pattern."
        )
        sentences.append(signal_note)
        sentences.append(
            "Try a steady side-on clip with the whole body in frame. "
            "A useful walk is about 5 to 15 seconds. "
            "The server accepts a longer clip, up to 120 seconds."
        )
        return " ".join(sentences)

    frame_pairs = max(0, int(measurements.get("frameCount", 0)) - 1)
    sentences.append(
        f"Across {frame_pairs} frame comparisons, {subject}'s movement scored "
        f"{overall} out of 100 overall."
    )

    scored_parts = [
        f"{FACTOR_LABELS[name]} {score} out of 100"
        for name, score in factors.items()
        if score is not None
    ]
    if scored_parts:
        sentences.append(f"That comes from {', '.join(scored_parts)}.")

    weakest = lowest_scored_factor(factors)
    if weakest and len(scored_parts) > 1:
        sentences.append(
            f"The lowest measured factor was {FACTOR_LABELS[weakest[0]]} at {weakest[1]} out of 100."
        )

    if previous_overall is not None:
        difference = round(overall - previous_overall, 1)
        if abs(difference) < 1:
            sentences.append("That is close to the previous saved walk.")
        elif difference < 0:
            sentences.append(
                f"That is {abs(difference)} points lower than the previous saved walk."
            )
        else:
            sentences.append(
                f"That is {difference} points higher than the previous saved walk."
            )
    else:
        sentences.append("There is no earlier saved walk to compare against yet.")

    unscored = [FACTOR_LABELS[name] for name, score in factors.items() if score is None]
    if unscored:
        sentences.append(f"Not scored in this clip: {', '.join(unscored)}.")

    if signal_quality == "limited":
        sentences.append(signal_note)

    if concerning:
        sentences.append(
            "This change is worth raising with a qualified veterinarian, who can examine "
            "what a video cannot show."
        )

    return " ".join(sentences)


def build_limitations(pipeline: str, signal_quality: str) -> str:
    """Write the caveat text that always travels with the observation."""

    parts = [
        "SilverPaws AI is observational educational software. This is not a diagnosis and "
        "cannot rule out pain or injury."
    ]

    if pipeline == "opencv-motion":
        parts.append(
            "No pet pose landmarks were used for this clip, so the measurements describe "
            "overall picture movement rather than individual limbs."
        )
    elif pipeline == "rtmpose-ap10k":
        parts.append(
            "Limb points come from RTMPose-m, a published model trained on the AP-10K "
            "animal pose dataset. SilverPaws did not train it. For dogs, AP-10K's own "
            "notes say its hip and knee labels follow a visual convention rather than "
            "a veterinary bone name. These values are not a diagnosis and do not detect pain or injury."
        )
    else:
        parts.append(
            "Pose landmarks were not produced by the quadruped model, so they are not a "
            "veterinary measurement."
        )

    if signal_quality != "good":
        parts.append("Treat these values as a rough read rather than a measurement you can rely on.")

    parts.append(
        "For pain, sudden weakness, collapse, or breathing trouble, contact a veterinarian "
        "or emergency clinic directly instead of waiting for an app result."
    )
    return " ".join(parts)
