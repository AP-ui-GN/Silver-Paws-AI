# Model card

SilverPaws measures a walking clip. It does not diagnose pain, injury, or disease.

## What runs

| Pipeline | When | What it measures |
| --- | --- | --- |
| `dog-pose` | torch, transformers, and the weights load | A dog box, then 17 AP-10K keypoints |
| `opencv-motion` | pose cannot run, or pose throws | Frame-to-frame picture change only |

New results do not use the older human-pose pipeline name. Saved walks that
used it still validate.

**Dog detector.** `PekingU/rtdetr_r50vd_coco_o365` (`RTDetrForObjectDetection`).
The model card on Hugging Face lists Apache-2.0. The dog class id is read
from `config.id2label`. It is not hard-coded. A box is kept at
`DOG_DETECT_THRESHOLD` 0.3.

**Pose.** `usyd-community/vitpose-plus-base` (`VitPoseForPoseEstimation`),
the ViTPose++ base checkpoint. The Transformers documentation read on
October 21, 2026 lists dataset index 3 as AP-10K and 4 as APT-36K. This
pipeline passes index 3. The checkpoint `id2label` is human COCO names and
is not used. Keypoint order is the AP-10K list in `gait_engine/pose_backend.py`.

A check image from one side-view dog clip showed the dog box on the dog, and
the drawn names did not sit on the body parts those names mean. Treat pose
quality on pet dogs as unproven until that order is confirmed and a labeled
set is measured.

Both models run on the server. The browser only uploads the clip.

## What is not validated

- Keypoint order on pet dogs, until the pose-check images are reviewed
- Stride symmetry as a clinical measure
- Any link between a score and pain, injury, or disease

Placeholder peak, spacing, and phase cutoffs are in `docs/GAIT_METRICS.md`.

## Fallback

If torch, transformers, or the weights are missing, or pose throws, the clip
is still measured with OpenCV frame difference. `diagnostics.poseSkipReason`
says why. The request does not fail because pose failed.

## Cache

```bash
pip install -r requirements.txt
python scripts/cache_models.py
```

Weights go to `HF_HOME`, default `models/hf`. That directory is gitignored.

## Time and memory

On this CPU, a 15.000-second 30 fps file made by repeating a 5-second clip
took 40.127 seconds end to end (`scripts/time_clip.py`: sample 0.949 s,
pose including weight load 39.162 s, gait math 0.015 s). Peak RSS was
1665.3 MB. One-shot `analyze_clip.py` on the same file took 37.543 seconds.
Loading both models in a new process, without a clip, took 4.02 seconds of
wall time. The Docker image was not built, so hosted RAM is not measured.
Details are in `docs/HOSTING.md`.
