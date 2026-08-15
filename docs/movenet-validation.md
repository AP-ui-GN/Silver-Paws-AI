# MoveNet Thunder validation

This is the first SilverPaws AI milestone: run pretrained MoveNet Thunder on
video frames, print the detected keypoints, and calculate one explainable
left/right motion metric. It is intentionally independent of FastAPI,
Firestore, and any frontend.

## Run locally

Use Python 3.10 or 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate_movenet.py path/to/pet-walking-video.mp4
```

For a quick smoke test or a machine with limited compute:

```bash
python scripts/validate_movenet.py path/to/video.mp4 --max-frames 30
```

Save all keypoints and the summary metric as JSON:

```bash
python scripts/validate_movenet.py path/to/video.mp4 \
  --output-json outputs/first-validation.json
```

The first run downloads MoveNet Thunder from TensorFlow Hub and may take
longer than subsequent runs.

## Run in Google Colab

Upload the `gait_engine/` directory, `scripts/validate_movenet.py`, and a
walking video into the Colab runtime, then run:

```python
%pip install -r requirements.txt
!python scripts/validate_movenet.py /content/pet-walking-video.mp4
```

## Metric definition

For each frame, the validator reads MoveNet's left and right ankle `y`
coordinates. It sums the absolute frame-to-frame vertical movement for each
side, then calculates:

```text
symmetry = 1 - abs(left_motion - right_motion) / (left_motion + right_motion)
```

The value is clamped to `[0, 1]`; higher means the two detected sides moved
more similarly. Low-confidence ankle coordinates are excluded from adjacent
frame comparisons. If there are not at least two confident frames for each
ankle, or there is no measurable motion, the validator reports the metric as
unavailable rather than treating missing signal as perfect symmetry.

## Important validation limitation

MoveNet Thunder is a pretrained **human-pose** model. The first script proves
that model loading, video decoding, keypoint extraction, and metric
calculation work, but it does not prove reliable dog/cat pose detection.
Before using the score for a Congressional App Challenge demo or any
vet-facing report, compare it against labeled pet videos and consider a
pet-specific pose model if the detections are not stable. The output is not a
diagnosis.
