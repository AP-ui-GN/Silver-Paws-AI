# How AI is used in SilverPaws

SilverPaws combines RT-DETR dog detection and identity tracking with QuadPose F2, a pinned ONNX model that returns 17 AP-10K-order animal landmarks, plus frame-to-frame OpenCV motion. Derived gait values and thresholds are experimental and have not been validated on a labeled set of pet-dog walking clips. Scores and notes use fixed formulas. An optional language model may reword the note without changing measured values.

This page is generated from `lib/ai-use/registry.json`. Edit that file and run `node scripts/sync-ai-use.mjs`. Do not edit the copies by hand.

Pose landmarks are described further in `docs/MODEL_CARD.md`.

## dog-detector

**What it is.** RT-DETR, PekingU/rtdetr_r50vd_coco_o365, an object detector. The model card license is Apache-2.0.

**What it does.** When torch and the weights are installed, the server finds dog boxes in sampled frames. The dog class id is read from the model labels. It also notes when a person box is present. That note is informational.

**What it doesn't do.** It does not name a condition, decide which leg is weaker, or choose the wellness score.

Code: `gait_engine/pose_backend.py`

## pose-model

**What it is.** QuadPose F2, a published ONNX quadruped-pose model from EstevanSL/snapml-quadruped-pose at commit 52f0329b5c9af513b5a8f2820aaea6bbd945d0c0. The pinned checkpoint SHA-256 is f3807433962d8abcee18f1bd45e5ff9e56bd899768b03a6996c3db4ebd12b884. The publisher labels the code and weights Apache-2.0 and says the model was trained on AP-10K (annotations CC BY 4.0). SilverPaws does not train this model.

**What it does.** When the verified ONNX checkpoint and RT-DETR detector weights are installed, the server estimates 17 AP-10K-order animal landmarks inside the tracked dog's box. Heatmap peak scores are not calibrated probabilities. Derived gait values use experimental formulas and cutoffs.

**What it doesn't do.** It does not diagnose a condition or detect pain. Its performance has not been validated on a labeled set of pet-dog walking videos, and the gait metrics are not clinically validated. Missing or low-confidence points are not treated as measurements.

Code: `gait_engine/pose_backend.py`

## motion-fallback

**What it is.** Standard OpenCV frame-difference analysis. This is not a learned model.

**What it does.** The server compares consecutive frames and records how much the picture changed. This runs on every clip. When pose is unavailable, it is the only movement measurement. When pose runs, this measurement still supplies movement consistency and activity.

**What it doesn't do.** It does not find limbs or keypoints, and it is not an AI model.

Code: `gait_engine/motion.py`

## scoring

**What it is.** Fixed formulas and weights in the wellness module.

**What it does.** Turns the measured values into factor scores and one overall indicator from 0 to 100. A missing measurement is left out. It is not treated as zero.

**What it doesn't do.** No AI model chooses or adjusts these scores.

Code: `gait_engine/wellness.py`

## observation-rules

**What it is.** Sentence templates in the wellness module.

**What it does.** Builds the plain-language note from the measured values and the scores.

**What it doesn't do.** It does not invent numbers, name a condition, or call a language model.

Code: `gait_engine/wellness.py`

## llm-rewrite

**What it is.** An optional language-model call on the analysis server.

**What it does.** When SILVERPAWS_LLM_URL and SILVERPAWS_LLM_MODEL are set, the server asks that provider to rephrase the rule-based note. The reply is shown only if it passes validation.

**What it doesn't do.** It is off when those variables are unset. It cannot add a measurement, name a condition, or drop a veterinarian recommendation. A failed or invalid reply is discarded and the rule-based note is shown.

Code: `artifacts/api-server/src/lib/explanation.ts`

## development

**What it is.** AI coding assistants used while building the app.

**What it does.** Parts of this app's code and documentation were written with AI coding assistants and reviewed by the team.

**What it doesn't do.** This is not a model that runs on a clip. It does not measure a pet or write the note an owner sees from a walk. The team lead confirms this entry's final wording before release.

Code: the repository as a whole, not one clip.
