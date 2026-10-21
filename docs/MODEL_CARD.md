# SilverPaws model card

SilverPaws measures a short walking clip and writes a wellness note. It does
not diagnose pain, injury, or disease. A concerning change tells the owner to
ask a veterinarian.

## What runs

Two paths exist. The result names the one that ran. The app does not swap them
silently, and it does not label a human pose model as the dog measurement.

| Path | When | What it measures |
| --- | --- | --- |
| `quadpose` | onnxruntime is installed and the pinned QuadPose F2 checkpoint loads | 17 quadruped keypoints. Hind paws feed the left and right motion measurements. Hips feed hip stability. |
| `opencv-motion` | onnxruntime is missing, or the checkpoint cannot be loaded | Frame-to-frame picture change only |

**QuadPose F2** is a quadruped pose model published by Sausage Labs in
[snapml-quadruped-pose](https://github.com/EstevanSL/snapml-quadruped-pose),
file `models/quadpose_f2.onnx` at commit `52f0329b5c9af513b5a8f2820aaea6bbd945d0c0`.
The weights are Apache-2.0, Copyright 2026 Sausage Labs. The publisher states
that the model was trained on AP-10K. AP-10K (Yu et al., NeurIPS 2021) is an
animal pose dataset whose authors describe 54 species, including dogs, with
17 body keypoints. Annotation license: CC BY 4.0. This repository does not
contain that dataset and does not train or fine-tune a network.

The publisher's NOTICE also attributes a ViTPose teacher (Apache-2.0) and
MobileNetV2 ImageNet initialization. Those are the publisher's training
ingredients. This repo only runs the published ONNX file.

The graph input is a 256×256 RGB crop, values 0–255. The output is 17
heatmaps. Joint order is the AP-10K order:

`L_Eye`, `R_Eye`, `Nose`, `Neck`, `Root of tail`, `L_Shoulder`, `L_Elbow`,
`L_F_Paw`, `R_Shoulder`, `R_Elbow`, `R_F_Paw`, `L_Hip`, `L_Knee`, `L_B_Paw`,
`R_Hip`, `R_Knee`, `R_B_Paw`.

How those landmarks fill the existing measurements:

| Measurement | Landmark | AP-10K name |
| --- | --- | --- |
| `leftAnkleMotion` | left hind paw | `L_B_Paw` |
| `rightAnkleMotion` | right hind paw | `R_B_Paw` |
| `hipStability` | left and right hips, kept separate and then combined only as the hip line | `L_Hip`, `R_Hip` |

The field names still say "ankle" because that is the measurement the app
already stores. The points are hind paws, not human ankles. Left and right
are never averaged into one limb. `L_Knee` and `R_Knee` are not used for
either measurement.

The published model is top-down: it expects a crop around one animal. Snap's
animal detector is not shipped; its license is not Apache-2.0. Each frame is
cropped to the region that changed since the previous frame. If that region
is tiny or almost the whole frame, the whole frame is sent. A bad crop shows
up as low confidence, and the limb values stay unset.

**OpenCV frame difference** downscales the clip to 320 px, blurs it, and records
the mean absolute grayscale change between frames. There are no limbs in that
path. It still runs when QuadPose runs, and it supplies movement consistency
and activity. Symmetry, mobility, and pose confidence stay unset when pose
does not run.

Inference runs on the server. The phone and the browser only upload the clip
and store the JSON. `modelInfo.runsOn` is always `"server"`. `modelInfo`
for a pose result is pipeline `quadpose`, model name `QuadPose F2`, and the
pinned commit as `modelVersion`.

MoveNet Thunder remains in the repository as a human-pose loader for the old
`scripts/validate_movenet.py` check. The analysis pipeline does not call it.
A dog clip is not reported as `movenet`.

## Versions

| Piece | Pinned version | Python |
| --- | --- | --- |
| QuadPose F2 weights | commit `52f0329b5c9af513`, SHA-256 `f3807433962d8abcee18f1bd45e5ff9e56bd899768b03a6996c3db4ebd12b884` | downloaded file |
| onnxruntime | 1.20.1 | 3.10, 3.11, or 3.12. The API image uses 3.11. |
| OpenCV | 4.10.0.84 | same |
| NumPy | 1.26.4 | same |

`requirements.txt` is the pose install. `requirements-opencv.txt` is the
motion-only install. Do not float these versions: a different build would
change the numbers without saying so.

Warm the QuadPose cache before the first request, at build or deploy time:

```bash
python scripts/cache_quadpose.py
```

That writes `models/quadpose/quadpose_f2.onnx` (or `SILVERPAWS_QUADPOSE_CACHE`).
The loader checks the SHA-256 before it runs the file. If the cache is empty
and onnxruntime is installed, the first pose request downloads the same pinned
file once. If onnxruntime is not installed, the clip is labeled
`opencv-motion` and no download is attempted.

## Intended use

- A pet owner films one pet, from the side, with the whole body in frame and enough light to see the legs. A useful walk is about 5 to 15 seconds. The server accepts a longer clip, up to 120 seconds.
- The note is something to compare with an earlier walk and, if the change is
  large, to take to a veterinarian.
- It is educational observation software.

## What this model does not do

QuadPose was trained on animal photographs, not on the individual dog in the
clip, and not in this repository. It does not diagnose pain, injury, or
disease. It does not decide the wellness score. It does not run on the phone.

A landmark that is missing, outside the frame, or below the confidence gate
is left unmeasured. It is not filled in, and it is not stored as zero. A
measured zero is only a real detection whose position did not change.

The model is not a clinical gait system. One angle of one short clip is not
the whole animal. Other species in AP-10K can pull a keypoint onto the wrong
place when the dog is partly hidden, facing the camera, or small in the frame.

## Confidence gating

Two thresholds are already in the pipeline and were kept:

- `0.2` — a single keypoint below this is ignored inside hip stability and
  the hind-paw motion measurements. It is not treated as a real joint position.
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
hind-paw motion (stored as left and right ankle motion), stride symmetry,
asymmetry, and hip stability.

When QuadPose runs, the API also returns `measurements.poseKeypoints`: a
compact per-joint mean of source-frame-normalized `(x, y)` positions across
frames whose mean pose confidence reaches the existing trust threshold. The
model maps its crop back onto the source frame before that average. Individual
points must also pass the existing keypoint-confidence threshold and fall
inside the frame. These coordinates are a visual summary, not a frame-by-frame
recording, and they do not feed or change any score. They are saved with the
local analysis record so the detail screen can render the same summary later.
The app does not retain or replay the uploaded video. The OpenCV-only path
has no pose points; its detail screen instead displays frame motion coverage.

**Interpreted:** factor scores, the overall 0–100 indicator, the observation
sentence, and the "ask a veterinarian" flag. The observation may quote
measured numbers. It does not name a condition. An optional language model
may only rephrase that sentence, and `validateExplanation()` rejects invented
numbers, diagnoses, certainty, and a dropped vet recommendation.

## Known failure modes

- The pet is facing the camera, partly out of frame, or wearing something
  that hides the legs. Pose confidence drops and limb values are not measured.
- The crop is the whole frame because the camera moved, or the dog is small.
  Keypoints can land in the wrong place. Low confidence leaves the limbs unset.
- The clip is dark, blown out, very small, or mostly still. A quality note
  explains what to change. Scores from a still clip are withheld.
- A confident keypoint can still be the wrong joint. Treat limb numbers as a
  rough comparison with the same camera setup, not as a clinical measurement.
- One angle of one short clip is not the whole animal.
- OpenCV motion cannot tell left from right. Those factors stay unset.
- The first 120 pose frames are the ones that are read, not a sample spread
  across a long clip.

## What this is not

Not a diagnosis. Not an emergency service. Not a pain or injury detector.
For pain, collapse, breathing trouble, or a sudden change, contact a
veterinarian directly.
