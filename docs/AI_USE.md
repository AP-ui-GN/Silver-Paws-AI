# How AI is used in SilverPaws

SilverPaws can use one pose-detection model, RTMPose-m trained on AP-10K, to find animal body points in a clip. Every clip also gets a standard frame-to-frame motion measurement. Scores and the note come from fixed formulas. An optional language model can reword the note when the server is configured for it; it cannot change the numbers.

This page is generated from `lib/ai-use/registry.json`. Edit that file and run `node scripts/sync-ai-use.mjs`. Do not edit the copies by hand.

Pose landmarks are described further in `docs/MODEL_CARD.md`.

## pose-model

**What it is.** RTMPose-m, a pose model published by OpenMMLab in MMPose. The checkpoint is rtmpose-m_simcc-ap10k_pt-aic-coco_210e-256x256-7a041aa1_20230206. MMPose says it was trained on AP-10K and reports 72.2 AP on that dataset. AP-10K is the animal pose dataset of 10,015 images from 23 families and 54 species described by Yu et al. (NeurIPS 2021 Datasets and Benchmarks). The checkpoint name records a CSPNeXt backbone initialized from an AI Challenger and COCO pretrain, which is what the published MMPose config does. SilverPaws did not train this model and has no private dog videos.

**What it does.** When ONNX Runtime is installed and this checkpoint loads, the analysis server runs it on video frames. It returns the 17 AP-10K keypoints (eyes, nose, neck, tail root, shoulders, elbows, front paws, hips, knees, and back paws), each with a position and a confidence. It does not run on the phone. Hind-paw stride uses L_B_Paw and R_B_Paw. Fore-paw motion uses L_F_Paw and R_F_Paw.

**What it doesn't do.** It outputs positions and confidences only. It does not name a condition, detect pain or injury, or choose the wellness score. It does not use MoveNet or relabel a human skeleton as a dog.

Code: `gait_engine/quadruped.py`

## motion-fallback

**What it is.** Standard OpenCV frame-difference analysis. This is not a learned model.

**What it does.** The server compares consecutive frames and records how much the picture changed. This runs on every clip. When the pose model is unavailable or below the confidence gate, it is the only movement measurement. When the pose model runs, this measurement still supplies movement consistency and activity.

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
