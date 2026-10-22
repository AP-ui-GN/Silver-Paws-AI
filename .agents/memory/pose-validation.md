---
name: Pet pose validation
description: The dog detector and animal pose model are unproven on pet dogs until a labeled set is measured.
---

The current pose path uses a dog detector and an AP-10K keypoint model.
A single side-view check can show a box on the dog while the keypoint names
do not match the body parts. Do not treat a symmetry number from that model
as validated.

**Why:** Pose quality on pet dogs is unproven until labeled clips are measured
and the keypoint order is confirmed from the pose-check images.

**How to apply:** Keep missing measurements null. Do not mix pipelines in one
trend series. Say ask a veterinarian when a measured change is concerning.
Do not name a condition.
