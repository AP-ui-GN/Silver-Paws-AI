# SilverPaws model card

SilverPaws measures a short walking clip and writes a wellness note. It does
not diagnose pain, injury, or disease. A concerning change tells the owner to
ask a veterinarian.

## What runs

Two paths exist. The result names the one that ran. The app does not swap them
silently.

| Path | When | What it measures |
| --- | --- | --- |
| `rtmpose-ap10k` | ONNX Runtime is installed and the published RTMPose-m checkpoint loads | 17 AP-10K animal keypoints, then hip-point steadiness and left/right paw motion |
| `opencv-motion` | ONNX Runtime is missing, the checkpoint cannot load, or pose confidence is below the gate | Frame-to-frame picture change only |

**RTMPose-m** is OpenMMLab's animal pose model from MMPose, checkpoint
`rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206`.
Input is 256×256. Output is SimCC maps for 17 keypoints. The keypoint names
and order are the AP-10K labels in the MMPose dataset meta:

`L_Eye`, `R_Eye`, `Nose`, `Neck`, `Root of tail`, `L_Shoulder`, `L_Elbow`,
`L_F_Paw`, `R_Shoulder`, `R_Elbow`, `R_F_Paw`, `L_Hip`, `L_Knee`, `L_B_Paw`,
`R_Hip`, `R_Knee`, `R_B_Paw`.

MMPose's RTMPose project page says this checkpoint was trained on AP-10K and
lists 72.2 AP on that dataset. That figure is theirs, not a SilverPaws result.
AP-10K, from its own repository, is 10,015 images from 23 animal families and
54 species (Yu et al., NeurIPS 2021 Datasets and Benchmarks). The checkpoint
name and the published training config initialize the CSPNeXt backbone from a
model trained on AI Challenger and COCO. SilverPaws did not train or fine-tune
this model. This project has no private dog videos.

The clip is treated as one animal filling the frame, which is the filming
instruction. There is no second detector. Hind-paw stride uses `L_B_Paw` and
`R_B_Paw`. Fore-paw motion uses `L_F_Paw` and `R_F_Paw`. Hip-point steadiness
uses `L_Hip` and `R_Hip`. AP-10K's own notes say that for digitigrade animals,
including dogs, those hip and knee labels follow a visual convention rather
than a veterinary bone name. The app keeps the model's names and does not
rename them to ankles.

**OpenCV frame difference** downscales the clip to 320 px, blurs it, and records
the mean absolute grayscale change between frames. There are no limbs in that
path. Symmetry, mobility, and pose confidence stay unset.

Inference runs on the server. The phone and the browser only upload the clip
and store the JSON. `modelInfo.runsOn` is always `"server"`.

## Versions

| Piece | Pinned version | Python |
| --- | --- | --- |
| ONNX Runtime | 1.20.1 | 3.10–3.12 |
| OpenCV | 4.10.0.84 | 3.10–3.12 for the motion-only install |
| NumPy | 1.26.4 | same as the install you chose |
| RTMPose-m AP-10K | `7a041aa1_20230206` | the ONNX file above |

`requirements.txt` is the pose install. `requirements-opencv.txt` is the
motion-only install. Do not float these versions: a different build would
change the numbers without saying so.

Warm the checkpoint cache before the first request, at build or deploy time:

```bash
python scripts/cache_quadruped.py
```

That fills `models/rtmpose` (or `SILVERPAWS_RTMPOSE_CACHE`). `load_quadruped()`
reads the same file, so a warmed cache is reused. If the cache is empty and
ONNX Runtime is installed, the first pose request still downloads the
checkpoint once. If ONNX Runtime is not installed, the clip is labeled
`opencv-motion` and no download is attempted.

## Intended use

- A pet owner films one pet, from the side, with the whole body in frame and enough light to see the legs. A useful walk is about 5 to 15 seconds. The server accepts a longer clip, up to 120 seconds.
- The note is something to compare with an earlier walk and, if the change is
  large, to take to a veterinarian.
- It is educational observation software.

## What this model is not

It was not trained by SilverPaws. A dog breed that is rare in AP-10K can still
be a weak detection. Low confidence is reported as not measured. It is not
filled in, and it is not shown as zero.

## Confidence gating

Two thresholds are already in the pipeline and were kept:

- `0.2` — a single keypoint below this is ignored inside hip-point steadiness
  and paw motion. It is not treated as a real joint position.
- `0.3` — mean keypoint confidence. Below this, or when no frame reaches it,
  limb measurements stay unset (`null`), `lowConfidence` is true, and the
  result screen says **Low confidence — try a clearer clip**.

The stored confidence is the SimCC score from the checkpoint, clamped to 0–1
so the API contract stays in that range. Clamping does not turn a low score
into a passing one.

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
fore-paw motion, hind-paw motion, hind-paw stride symmetry, asymmetry, and
hip-point steadiness.

When RTMPose-m runs, the API also returns `measurements.poseKeypoints`: a
compact per-joint mean of source-frame-normalized `(x, y)` positions across
frames whose mean pose confidence reaches the existing trust threshold.
Individual points must also pass the existing keypoint-confidence threshold
and fall inside the frame. These coordinates are a visual summary, not a
frame-by-frame recording, and they do not feed or change any score. They are
saved with the local analysis record so the detail screen can render the same
summary later. The app does not retain or replay the uploaded video. The
OpenCV-only path has no pose points; its detail screen instead displays frame
motion coverage.

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
- The animal does not fill the frame. The model sees the whole picture as one
  box, so a small subject can fall below the confidence gate.
- AP-10K covers many species. A high score is still one camera angle, not a
  clinical measurement.
- One angle of one short clip is not the whole animal.
- OpenCV motion cannot tell left from right. Those factors stay unset.
- The first 120 pose frames are the ones that are read, not a sample spread
  across a long clip.

## What this is not

Not a diagnosis. Not an emergency service. Not a pain or injury detector.
For pain, collapse, breathing trouble, or a sudden change, contact a
veterinarian directly.
