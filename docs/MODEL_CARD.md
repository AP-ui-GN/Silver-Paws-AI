# SilverPaws model card

SilverPaws measures a short walking clip and writes a wellness note. It does
not diagnose pain, injury, or disease. A concerning change tells the owner to
ask a veterinarian.

## What runs

Two paths exist. The result names the one that ran. The app does not swap them
silently.

| Path | When | What it measures |
| --- | --- | --- |
| `movenet` | TensorFlow is installed and MoveNet Thunder loads | 17 body keypoints, then hip stability and left/right ankle motion |
| `opencv-motion` | TensorFlow is missing, or the pose model cannot run | Frame-to-frame picture change only |

**MoveNet Thunder** is Google's single-pose model, TensorFlow Hub
`movenet/singlepose/thunder/4`. Input is 256×256. Output is 17 keypoints in
`(y, x, confidence)` order, the same labels the model was trained with (nose,
eyes, ears, shoulders, elbows, wrists, hips, knees, ankles).

**OpenCV frame difference** downscales the clip to 320 px, blurs it, and records
the mean absolute grayscale change between frames. There are no limbs in that
path. Symmetry, mobility, and pose confidence stay unset.

Inference runs on the server. The phone and the browser only upload the clip
and store the JSON. `modelInfo.runsOn` is always `"server"`.

## Versions

| Piece | Pinned version | Python |
| --- | --- | --- |
| TensorFlow | 2.15.1 | 3.10 or 3.11 only. Not 3.12. |
| TensorFlow Hub | 0.16.1 | same |
| OpenCV | 4.10.0.84 | 3.10–3.12 for the motion-only install |
| NumPy | 1.26.4 | same as the install you chose |

`requirements.txt` is the pose install. `requirements-opencv.txt` is the
motion-only install. Do not float these versions: a different build would
change the numbers without saying so.

Warm the MoveNet cache before the first request, at build or deploy time:

```bash
python scripts/cache_movenet.py
```

That fills `models/tfhub` (or `SILVERPAWS_MOVENET_CACHE`). `load_movenet()`
points `TFHUB_CACHE_DIR` at the same directory, so a warmed cache is reused.
If the cache is empty and TensorFlow is installed, the first pose request
still downloads Thunder once. If TensorFlow is not installed, the clip is
labeled `opencv-motion` and no download is attempted.

## Intended use

- A pet owner films one pet, from the side, for about 5 to 60 seconds, with
  the whole body in frame and enough light to see the legs.
- The note is something to compare with an earlier walk and, if the change is
  large, to take to a veterinarian.
- It is educational observation software.

## Human-trained limits

MoveNet was trained on human bodies. A dog or cat is not that training set.
Legs, a tail, and a coat can be assigned to the wrong human joint, or to none.
Low confidence is reported as not measured. It is not filled in, and it is not
shown as zero.

## Confidence gating

Two thresholds are already in the pipeline and were kept:

- `0.2` — a single keypoint below this is ignored inside hip stability and
  ankle motion. It is not treated as a real joint position.
- `0.3` — mean keypoint confidence. Below this, or when no frame reaches it,
  limb measurements stay unset (`null`), `lowConfidence` is true, and the
  result screen says **Low confidence — try a clearer clip**.

`modelConfidence` is that mean, from 0 to 1. `null` means pose did not run.
The older `confidence` field is the same number on a 0–100 scale so existing
screens keep working.

`framesUsed` counts frames whose mean keypoint confidence reached 0.3.
`framesTotal` is how many frames the model ran on (at most 120). Both are
`null` when pose did not run. A used-count of 0 means no frame passed. That
is a count, not a missing value rewritten as a score.

## Clip-quality pre-check

Before scoring, the pipeline looks at duration, resolution, brightness, and
whether enough of the clip actually moved. Failures become `qualityNotes`:
short sentences that tell the owner what to film next, including "Film from
the side with the whole body in frame." An unknown duration (no frame rate)
is not described as 0 seconds. A clip can still be scored when a note is only
a warning. A clip that is too short or has no visible movement is not scored.

## What is measured vs interpreted

**Measured** (or explicitly not measured): frame count, duration, motion mean
and spread, motion coverage, brightness used only for the quality note,
keypoint confidence, frames used, and — when pose confidence is high enough —
ankle motion, stride symmetry, asymmetry, and hip stability.

**Interpreted:** factor scores, the overall 0–100 indicator, the observation
sentence, and the "ask a veterinarian" flag. The observation may quote
measured numbers. It does not name a condition. An optional language model
may only rephrase that sentence, and `validateExplanation()` rejects invented
numbers, diagnoses, certainty, and a dropped vet recommendation.

## Known failure modes

- The pet is facing the camera, partly out of frame, or wearing something
  that hides the legs. Pose confidence drops and limb values are not measured.
- The clip is dark, blown out, very small, or mostly still. A quality note
  explains what to change. Scores from a still clip are withheld.
- MoveNet draws a human skeleton onto a pet. Even a high confidence can be
  the wrong joint. Treat limb numbers as a rough comparison with the same
  camera setup, not as a clinical measurement.
- One angle of one short clip is not the whole animal.
- OpenCV motion cannot tell left from right. Those factors stay unset.
- The first 120 pose frames are the ones that are read, not a sample spread
  across a long clip.

## What this is not

Not a diagnosis. Not an emergency service. Not a pain or injury detector.
For pain, collapse, breathing trouble, or a sudden change, contact a
veterinarian directly.
