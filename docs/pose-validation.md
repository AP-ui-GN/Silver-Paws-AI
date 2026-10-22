# Canine pose validation status

This document separates **model installation and output-schema checks** from
**real-world canine validation**.

## Current supported pose path

RT-DETR detects dog bounding boxes and the SilverPaws temporal tracker keeps a
selected dog identity across sampled frames. QuadPose F2 estimates 17 AP-10K-
order animal landmarks inside the tracked dog box. The canonical order and
pixel-coordinate conversion are in `gait_engine/pose_backend.py` and
`gait_engine/quadpose.py`.

Install and inspect model assets explicitly:

```bash
python -m pip install -r requirements.txt
python scripts/cache_models.py
python scripts/check_setup.py
```

The setup checker never downloads weights. The cache script downloads the
pinned RT-DETR detector and the pinned QuadPose F2 ONNX checkpoint; the latter
must match the documented SHA-256. The Docker build performs the same setup.
Inference rejects missing or mismatched QuadPose weights rather than silently
downloading them during an upload.

## What is verified by automation

- Keypoint schema, count, and index order are checked by unit tests.
- The adapter's normalized `(y, x, score)` to source-frame pixel
  `(x, y, score)` conversion is tested with deterministic synthetic heatmaps.
- The model cache path and SHA-256 verification are unit-tested.
- GitHub Actions builds the Docker image and runs the model on a blank frame,
  asserting that a finite 17×3 output is returned.
- The API is exercised with a synthetic moving-shape video to check its
  container and response contract.

These checks validate packaging, interface behavior, and output shape. They
do **not** establish keypoint accuracy on real dogs or validate gait metrics.

## What is not validated yet

No labeled set of pet-dog walking videos has been used to measure SilverPaws'
end-to-end pose or gait performance. The upstream model's reported AP-10K
benchmark uses the upstream evaluation protocol and must not be presented as
SilverPaws accuracy. Gait formulas and cutoffs remain experimental. There are
no supported claims of sensitivity, specificity, pain detection, injury
detection, or clinical usefulness.

Side-view footage can hide far-side limbs, and camera movement can change the
apparent motion independently of the dog. Physical distance is not estimated
from pixels without calibration. Unsupported or low-quality measurements must
remain unavailable rather than being replaced with zero.

## Repeatable evaluation procedure

When a suitably licensed, representative set becomes available:

1. Place clips in the gitignored `validation_clips/` directory.
2. Keep labels in `validation_clips/labels.csv` with columns
   `file,label,source,license,notes`.
3. Record the clip source, license, viewpoint, resolution, and known exclusions.
4. Compare predictions against documented ground truth, not confidence alone.
5. Report the number of clips, failure rate, track switches, measurement
   availability, and appropriate error metrics.
6. Keep upstream model benchmark numbers separate from SilverPaws end-to-end
   results.

Do not commit private videos or label files unless distribution rights and
privacy review allow it.
