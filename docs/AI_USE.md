# How AI is used in SilverPaws

SilverPaws can use one pose-detection model, MoveNet Thunder, to find body points in a clip. Every clip also gets a standard frame-to-frame motion measurement. Scores and the note come from fixed formulas. An optional language model can reword the note when the server is configured for it; it cannot change the numbers.

This page is generated from `lib/ai-use/registry.json`. Edit that file and run `node scripts/sync-ai-use.mjs`. Do not edit the copies by hand.

Pose landmarks are described further in `docs/MODEL_CARD.md`.

## pose-model

**What it is.** MoveNet Thunder, a machine-learning pose model published by Google on TensorFlow Hub as singlepose/thunder/4. It was trained on human bodies.

**What it does.** When TensorFlow is installed, the analysis server runs MoveNet on video frames. It returns 17 body keypoints, each with a position and a confidence. It does not run on the phone.

**What it doesn't do.** It outputs positions and confidences only. It does not name a condition, detect pain, or choose the wellness score.

Code: `gait_engine/movenet.py`

## motion-fallback

**What it is.** Standard OpenCV frame-difference analysis. This is not a learned model.

**What it does.** The server compares consecutive frames and records how much the picture changed. This runs on every clip. When MoveNet is unavailable, it is the only movement measurement. When MoveNet runs, this measurement still supplies movement consistency and activity.

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
