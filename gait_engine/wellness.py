"""Turns raw measurements into factor scores, an overall indicator, and text.

The measurement keys used here are the same camelCase keys the API returns, so
one vocabulary runs from this module through the server to the UI.

This is a wellness/observation layer. It describes what was measured. It never
names a condition, and it never claims certainty.
"""

from __future__ import annotations

from .features import movement_consistency

# Weight of each factor inside the overall indicator. Only factors that were
# actually scored take part; the remaining weights are renormalized. A factor
# without an entry here is never counted, so a new factor needs a new weight.
#
# These are the initial engineering values used to get the pipeline running
# end to end. Calibrating them is Sudarshan's task (see TEAM_TASKS.md).
DEFAULT_WEIGHTS: dict[str, float] = {
    "movementConsistency": 0.45,
    "symmetry": 0.35,
    "activity": 0.20,
}

FACTOR_LABELS: dict[str, str] = {
    "movementConsistency": "movement consistency",
    "symmetry": "stride symmetry",
    "mobility": "mobility",
    "activity": "activity",
    "historicalChange": "change from baseline",
}

# An overall drop of at least this many points against the previous saved walk is
# worth raising with a veterinarian. It is a prompt to ask, never a diagnosis.
CONCERNING_DROP = 10.0

# Measured left/right asymmetry (percent) that is worth raising, when the
# symmetry measurement was reliable enough to report.
CONCERNING_ASYMMETRY = 20.0


def _to_score(value: float | None) -> float | None:
    """Convert a 0-1 measurement into a rounded 0-100 factor score."""

    if value is None:
        return None
    return round(max(0.0, min(1.0, value)) * 100, 1)


# ==================================================
# TEAM TASK: SUDARSHAN
# PURPOSE:
# Decide how mobility should be scored from the pose measurements the pipeline
# already saves (hipStability, leftAnkleMotion, rightAnkleMotion, strideSymmetry)
# and return a 0-100 score, or None when the clip has no usable pose signal.
# Add a "mobility" weight to DEFAULT_WEIGHTS once the score is defined, otherwise
# overall_score() will keep ignoring it.
# ==================================================
def mobility_factor(measurements: dict) -> float | None:
    """Not scored yet. Returning None keeps mobility out of the overall score."""

    return None


# ==================================================
# TEAM TASK: SUDARSHAN
# PURPOSE:
# Turn the change between this walk's overall score and the previous saved walk
# into a 0-100 factor, then add a "historicalChange" weight to DEFAULT_WEIGHTS.
# Decide how large a change should matter, and how to treat a first walk with no
# baseline (return None). The plain delta is already reported in the observation
# text, so this task is only about scoring it.
# ==================================================
def historical_change_factor(
    overall: float | None,
    previous_overall: float | None,
) -> float | None:
    """Not scored yet. Returning None keeps baseline change out of the score."""

    return None


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
            "Try a steady side-on clip of 5 to 60 seconds where the whole body stays in frame."
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
    else:
        parts.append(
            "Pose landmarks come from a model trained on human bodies, so limb detections "
            "on pets can be unreliable."
        )

    if signal_quality != "good":
        parts.append("Treat these values as a rough read rather than a measurement you can rely on.")

    parts.append(
        "For pain, sudden weakness, collapse, or breathing trouble, contact a veterinarian "
        "or emergency clinic directly instead of waiting for an app result."
    )
    return " ".join(parts)
