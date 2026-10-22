# Model card

SilverPaws measures a walking clip. It does not diagnose pain, injury, or disease.

## What runs

| Pipeline | When | What it measures |
| --- | --- | --- |
| `dog-pose` | torch, transformers, and the weights load | A dog box, then 17 COCO joints. This checkpoint has no AP-10K head. |
| `opencv-motion` | pose cannot run, or pose throws | Frame-to-frame picture change only |

New results do not use the older human-pose pipeline name. Saved walks that
used it still validate.

**Dog detector.** `PekingU/rtdetr_r50vd_coco_o365` (`RTDetrForObjectDetection`).
The model card on Hugging Face lists Apache-2.0. The dog class id is read
from `config.id2label`. It is not hard-coded. A box is kept at
`DOG_DETECT_THRESHOLD` 0.3.

**Pose.** `usyd-community/vitpose-plus-base` (`VitPoseForPoseEstimation`).
The Transformers docs list dataset index 3 as an AP-10K backbone expert.
The checkpoint file has one keypoint head. `config.id2label` and
`config.edges` are the 17 COCO human joints. Index 4 is `R_Ear`. The
original ViTPose++ training config defines a separate AP-10K head, and that
head is not in this file. Passing dataset index 3 does not change the
channel order.

On one side-view frame, channel 0 sat on the nose and channel 4 sat on the
ear, next to the head, not at the base of the tail. The pipeline therefore
names these channels with the COCO schema. It does not call channel 4
`root_of_tail`. Stride length, which needs the neck and the base of the
tail, stays unmeasured.

Both models run on the server. The browser only uploads the clip.

## What is not validated

- Pose quality on a labeled set of pet dogs. One side-view frame was compared with `config.id2label`. Channel 4 is the right ear (91.0 px from the nose, 352.6 px from the left hip on that frame). That is a naming check, not a validation set.
- Left versus right on a side view. `left_knee` on that frame scored 0.38.
- Stride length from this head. It has no neck and no base of the tail, so those numbers stay unmeasured.
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
