# Pose check

This is a visual check of the dog detector and the AP-10K pose model. It is
not a clinical validation.

```bash
python scripts/check_pose_backend.py path/to/dog-walk.mp4 --out outputs/pose-check/
```

The script writes eight frames with the dog box and the skeleton. It also
prints whether the nose is farther from the root of the tail than the eyes,
and whether the back paws sit below the hips. A failed check is reported.
It is not turned into a score.

Do not commit the video or the images. `outputs/` and `validation_clips/`
are gitignored.

Labeled clips, when you have them, go in `validation_clips/` with
`validation_clips/labels.csv`. Columns: `file,label,source,license,notes`.
`label` is `normal`, `mild`, or `significant`. See `TESTING.md`.
