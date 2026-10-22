# Model card

SilverPaws AI records observable movement patterns from a walking clip. It is a
wellness observation tool, not a veterinary diagnostic system. It does not
diagnose injury, pain, or disease.

## Current analysis path

| Component | Model / method | Role |
|---|---|---|
| Dog detector | RT-DETR, `PekingU/rtdetr_r50vd_coco_o365` | Finds dog bounding boxes in sampled frames |
| Dog identity | SilverPaws temporal association in `gait_engine/tracking.py` | Preserves the selected track and marks ambiguous or lost intervals |
| Pose estimator | QuadPose F2 ONNX, pinned source commit `52f0329b5c9af513b5a8f2820aaea6bbd945d0c0` | Estimates 17 AP-10K-order animal landmarks in the selected dog box |
| Motion fallback | OpenCV frame difference | Measures picture changes when the pose path is unavailable |
| Gait calculations | Deterministic functions in `gait_engine/gait.py` | Derives experimental movement observations from usable landmarks |
| Score and wording | Fixed formulas/templates in `gait_engine/wellness.py` | Summarizes observed values; optional LLM rewrite does not choose measurements |

The detector and pose estimator are separate models. QuadPose is called with
the existing tracked dog box; the motion fallback is not used as a dog detector.

## QuadPose F2 provenance and setup

- Upstream project: [EstevanSL/snapml-quadruped-pose](https://github.com/EstevanSL/snapml-quadruped-pose)
- Pinned source commit: `52f0329b5c9af513b5a8f2820aaea6bbd945d0c0`
- Checkpoint: `models/quadpose_f2.onnx`
- SHA-256: `f3807433962d8abcee18f1bd45e5ff9e56bd899768b03a6996c3db4ebd12b884`
- The upstream publisher labels the model code and weights Apache-2.0 and states
  that it was trained on AP-10K. AP-10K annotations are published under CC BY 4.0;
  see the [dataset repository](https://github.com/AlexTheBad/AP-10K).
- SilverPaws does not train or fine-tune QuadPose F2.
- Model weights are not committed to this repository. Install them explicitly:

```bash
pip install -r requirements.txt
python scripts/cache_models.py
python scripts/check_setup.py
```

The setup check reads the local caches and does not download weights. Inference
also requires an already-cached detector and a checksum-verified QuadPose
checkpoint; an upload must not trigger an implicit download. The default ONNX
cache is `models/quadpose/quadpose_f2.onnx`, overridable with
`SILVERPAWS_QUADPOSE_CACHE`. The detector is cached under `HF_HOME`.

## Keypoint output contract

QuadPose returns a 17-channel heatmap in the AP-10K order. SilverPaws maps its
decoder output to this canonical schema:

1. left eye
2. right eye
3. nose
4. neck
5. root of tail
6. left shoulder
7. left elbow
8. left front paw
9. right shoulder
10. right elbow
11. right front paw
12. left hip
13. left knee
14. left back paw
15. right hip
16. right knee
17. right back paw

The adapter converts normalized `(y, x, score)` output to source-frame pixel
`(x, y, score)` coordinates and rejects non-finite, low-score, and out-of-frame
points. Heatmap peak scores are **not calibrated probabilities**. The schema
name describes output ordering; it is not a guarantee that every point is
visible or accurate in a given frame.

The ONNX decoder and box crop are implemented in `gait_engine/quadpose.py`.
The RT-DETR detection and identity association remain in
`gait_engine/pose_backend.py`.

## Evaluation and limitations

The upstream project reports AP 0.6289 on its AP-10K validation split with
ground-truth boxes. See the upstream [benchmark and evaluation details](https://github.com/EstevanSL/snapml-quadruped-pose).
That number is **not a SilverPaws end-to-end result**: it does not measure the
combination of SilverPaws dog detection, tracking, decoding, and gait formulas.

SilverPaws has not validated the complete pose-and-gait pipeline on a labeled
set of pet-dog walking videos. There is no app-specific accuracy, sensitivity,
specificity, or clinical-performance claim. The formulas and cutoffs in
`docs/GAIT_METRICS.md` remain experimental and need an appropriate labeled
evaluation before their performance can be characterized.

Important boundaries:

- A point may be occluded, misplaced, or confused with another limb. The model's
  confidence-like heatmap peak is not a calibrated probability.
- A single side view can hide far-side limbs or make anatomical left/right
  difficult to confirm.
- The app estimates 2D movement. A pixel displacement is not physical distance.
- Stride excursion is reported in relative body-length units where supported;
  it is not a measurement in meters or centimeters.
- A camera that pans or shakes can change image motion independently of the dog.
- Derived gait metrics are experimental movement observations, not a diagnosis
  or validated medical screen.
- Insufficient or ambiguous data must produce a missing measurement and reason,
  not a fabricated zero.

The tests exercise coordinate conversion, output shape handling, checksum
checking, tracking decisions, and mathematical behavior on synthetic inputs.
Those tests do not establish real-world canine pose accuracy.

## Fallback

If the pose stack, detector assets, or checksum-verified checkpoint is not
available—or pose inference fails—the analysis may return the OpenCV
`opencv-motion` result if that path succeeds. The result identifies the active
pipeline and explains the pose skip. A motion-only result does not contain dog
landmarks and must not be mixed with pose-derived history as if the pipelines
were equivalent.

## Runtime and resource measurements

The old COCO/ViTPose path had a recorded CPU run of about 40 seconds and peak
resident memory around 1.7 GB, largely including model-loading overhead. Those
numbers are historical and **must not be treated as QuadPose F2 benchmarks**.
The current QuadPose integration and Docker deployment need their own measured
latency and memory results.

GitHub Actions builds the Docker image and runs a setup/readiness check plus a
synthetic-motion `POST /api/analyze` smoke request. The synthetic clip checks
container packaging and the API-to-Python response path; it is not a dog video
and does not validate canine pose accuracy or production-host memory.
