---
name: Pet pose validation
description: Durable guidance from testing MoveNet Thunder against public dog videos.
---

MoveNet Thunder is a human-pose model. On public dog footage it may fail to
detect the intended pet, especially when people are also visible; a high
symmetry score can represent a nearby human rather than the dog.

**Why:** Internet-video testing produced one clip with zero confident ankle
detections and another with a strong symmetry score even though the subject
identity was not guaranteed. Treat this as a model-selection and subject-
validation problem, not a tuning problem.

**How to apply:** Keep confidence gating and report "metric unavailable" when
there is insufficient signal. Before using results for a pet-facing workflow,
use a pet-specific pose model or an explicit subject-detection/cropping step
and evaluate on a labeled pet clip set.