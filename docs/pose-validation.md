# Pose check

This is a visual check of the dog detector and the pose head. It is not a
clinical validation.

```bash
python scripts/check_pose_backend.py path/to/dog-walk.mp4 --out outputs/pose-check/
```

The script writes eight frames. Each point is labeled with the checkpoint
name and its confidence. A point under the score cutoff is an open circle
and is not connected. The current head is COCO-17. Channel 4 is the right
ear. The base of the tail is not in the output, so the script does not
score a nose-to-tail distance.

On the side-view clip used here, the right ear was beside the nose and far
from the left hip. That is why an AP-10K label on channel 4 drew
`root_of_tail` on the head.

Do not commit the video or the images. `outputs/` and `validation_clips/`
are gitignored.

Labeled clips, when you have them, go in `validation_clips/` with
`validation_clips/labels.csv`. Columns: `file,label,source,license,notes`.
`label` is `normal`, `mild`, or `significant`. See `TESTING.md`.
