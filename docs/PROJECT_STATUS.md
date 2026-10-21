# SilverPaws AI — Project Status and Team Handoff

Date: September 17, 2026
Prepared for: Abhi, Sudarshan, Kavin

This document records what changed in the productionization pass, the measured
impact of those changes, and exactly what each teammate still needs to do. It
pairs with `TEAM_TASKS.md` (short task cards) and `TESTING.md` (how to verify).

The pose path described below as MoveNet is the earlier state. Dog clips are
now measured with RTMPose-m on AP-10K (`pipeline: "rtmpose-ap10k"`). See
`docs/MODEL_CARD.md`.

---

## 1. Where the project stood before this pass

| Area | Before |
| --- | --- |
| Analysis | The **Analyze** page generated random scores with `Math.random()` and saved them as if they were measurements |
| Python gait engine | Existed (`metrics.py`, `movenet.py`) but nothing in the app called it |
| API | One route: `/api/healthz` |
| Contract | `openapi.yaml` described `/api/analyze`, but no server or client code implemented it |
| Build | `pnpm typecheck` **failed** with 3 errors in `lib/api-zod` |
| Seed data | A fake pet ("Mabel") and a fake analysis were injected into every new browser |
| Tests | One Chromium test that only runs on Replit |
| Frontend | Four orphaned files (`analyze-client.ts`, `local-motion-probe.ts`, `wellness.ts`, `disclaimers.ts`) that nothing imported and that did not compile against `storage.ts` |

The gap that mattered most: the product showed pet owners numbers that were not
measured from their video.

---

## 2. What changed

### 2.1 Analysis pipeline (Python, `gait_engine/`)

| File | Status | What it does |
| --- | --- | --- |
| `motion.py` | **new** | Reads a clip with OpenCV, downsamples to 320 px, blurs, and records frame-to-frame grayscale change (0–1) |
| `features.py` | **new** | `motion_statistics` (mean, std, coverage), `movement_consistency` (1 − coefficient of variation), `hip_stability` (hip-line wobble from pose) |
| `wellness.py` | **new** | Factor scores 0–100, weighted overall indicator, concerning-change rule, rule-based observation text, limitation text |
| `pipeline.py` | **new** | Orchestrates: motion → optional MoveNet pose → measurements → signal quality → factors → overall → text. Produces the exact `AnalyzeResult` JSON in the OpenAPI contract |
| `metrics.py`, `movenet.py` | unchanged | Existing left/right ankle symmetry and MoveNet loader |
| `__init__.py` | updated | Exports the new modules |
| `explain.py`, `motion_fallback.py`, `test_engine.py` | **removed** | Half-finished duplicates from an earlier attempt that imported symbols that did not exist |

`scripts/analyze_clip.py` (**new**) is the process boundary: one clip in, one JSON
object out, exit code 2 for a bad clip and 1 for a pipeline failure.

Two pipelines are selected automatically and labeled in the result:

- `movenet` — pose landmarks available (TensorFlow installed) → symmetry can be scored
- `opencv-motion` — picture motion only → symmetry and mobility stay `null`

A `null` factor is shown as **"Not scored"**. It never means zero.

### 2.2 API (`artifacts/api-server/`)

| File | Status | What it does |
| --- | --- | --- |
| `src/routes/analyze.ts` | **new** | `POST /api/analyze`: reads multipart, validates file type/size, writes a temp file, runs the pipeline, deletes the temp file |
| `src/lib/multipart.ts` | **new** | Small multipart/form-data reader (npm registry was unreachable, so no `multer` dependency) |
| `src/lib/analysis-runner.ts` | **new** | Spawns Python (`.venv` first, then system), enforces `ANALYSIS_TIMEOUT_MS`, validates output against the generated Zod schema |
| `src/lib/explanation.ts` | **new** | Guard for any language-model rewrite: rejects invented numbers, diagnosis wording, certainty claims, links, and dropped vet advice. Falls back to the rule-based text |
| `tests/*.test.ts` | **new** | 18 tests, run with `pnpm --filter @workspace/api-server run test` |

Error mapping seen by the user:

| Case | HTTP | Message |
| --- | --- | --- |
| No file | 400 | "Choose a video file to analyze." |
| Not a video | 400 | "That file is not a video SilverPaws can read…" |
| Corrupt video | 400 | "This file could not be opened as a video. Try exporting it as MP4." |
| Too large | 413 | "…larger than the 60 MB beta limit…" |
| Python missing / crash / timeout | 502 | Plain sentence, details in server log |
| API unreachable | UI | "Could not reach the analysis service. Check that the API server is running." |

### 2.3 Frontend (`artifacts/silverpaws-beta/`)

| File | Status | What changed |
| --- | --- | --- |
| `src/pages/analyze.tsx` | rewritten | Real upload → API → save. Local checks for type, size, duration. Cancel on navigate-away. Stage text and elapsed time instead of a fake percentage |
| `src/lib/analysis-api.ts` | **new** | `checkClip`, `requestAnalysis`, `describeAnalysisError` |
| `src/lib/storage.ts` | extended | Stores `pipeline`, `signalQuality`, `overallScore`, `factors`, `measurements`, `weightsUsed`, `concerningChange`, `usedLlm`. Fake seed pet and analysis removed |
| `src/pages/history.tsx` | extended | Overall indicator, factor breakdown with weights, **raw measurements** grid separate from **interpretation**, vet-recommendation banner when `concerningChange` is true |
| `src/pages/home.tsx` | fixed | Uses the overall score; no longer shows "Age not set years" |
| `src/lib/report.ts` | extended | PDF now lists overall score, every factor, raw measurements, whether the text was rule-based or model-written |
| `src/components/app-shell.tsx` | extended | Persistent safety + emergency disclaimer footer on every page |
| `src/components/trend-panel.tsx` | mounted | Placeholder is now visible on History for Kavin to replace |
| `vite.config.ts` | extended | `/api` proxied to the API server in dev and preview |
| `analyze-client.ts`, `local-motion-probe.ts`, `wellness.ts` | **removed** | Orphaned duplicate pipeline living in UI code |

### 2.4 Mobile app (`mobile/`, Expo SDK 57, runs in Expo Go)

| File | Status | What it does |
| --- | --- | --- |
| `app/(tabs)/index.tsx` | **new** | Home: pets with latest score, add/edit, link to history |
| `app/(tabs)/analyze.tsx` | **new** | Pick pet → Record (camera) or Choose video → upload with real progress → saved result card |
| `app/(tabs)/history.tsx` | **new** | Saved walks, pet filter, mounts Kavin's `TrendPanel` |
| `app/(tabs)/settings.tsx` | **new** | API address (auto-detected from the Expo dev server), Test connection, delete local data, safety text |
| `app/history/[id].tsx` | **new** | Score, factor bars, raw-measurements grid, observation, limitations, vet banner, share sheet, delete |
| `app/pet/[id].tsx` | **new** | Create/edit pet; **Kavin** marker for validation messages |
| `src/lib/api.ts` | **new** | `guessApiUrl` from `Constants.expoConfig.hostUri`, `checkClip`, XHR upload with `onprogress`, `isAnalyzeResult` guard, `describeAnalysisError` |
| `src/lib/storage.ts` | **new** | AsyncStorage version of the web module; `toAnalysisRecord`, `findBaseline` |
| `src/lib/types.ts` | **new** | Mirrors `openapi.yaml` |
| `src/components/*` | **new** | `ui.tsx`, `score.tsx`, `disclaimer-footer.tsx`, `trend-panel.tsx` (**Kavin** placeholder) |
| `metro.config.js` | **new** | Pins Metro to `mobile/` so the pnpm workspace above is not watched |

The mobile app is a standalone npm project so Expo's exact React/React Native
pins never conflict with the web app's catalog. It talks to the same
`POST /api/analyze`; no scoring happens on the phone.

Also removed in this step: three orphaned files from a pre-existing attempt
that nothing imported (`api-server/src/lib/read-upload.ts`,
`run-python-analysis.ts`, `scripts/run_analysis.py`).

### 2.5 Shared libraries and docs

- `lib/api-zod` — fixed the 3 pre-existing type errors (DOM `File`/`Blob` lib, duplicate export)
- `lib/api-client-react` — exports `ApiError` so the UI can read server messages
- `README.md`, `ARCHITECTURE.md`, `TEAM_TASKS.md`, `TESTING.md` — rewritten to match the code
- `tests/test_features.py`, `tests/test_wellness.py` — 32 Python tests

---

## 3. Measured impact

All numbers below were produced by running the code, not estimated.

| Metric | Before | After |
| --- | --- | --- |
| `pnpm typecheck` | 3 errors | 0 errors |
| `pnpm build` | fails on typecheck | passes (API 1.4 MB bundle, app 357 KB JS) |
| Automated tests | 0 runnable locally | 50 (32 Python + 18 Node), all passing |
| Scores derived from video | 0 % (random) | 100 % — every displayed number traces to a measurement |
| API routes | 1 | 2 |
| Pipeline run on `tmp/walk.mp4` (45 frames, 15 fps) | n/a | 2.1 s end to end |
| Result for that clip | random | overall 91.4 · consistency 87.6 · activity 100 · symmetry *not scored* (no pose) |
| Fabricated seed records | 2 | 0 |
| Disclaimer coverage | Home + PDF | Every page footer + history detail + PDF + observation text |
| Platforms | Browser only | Browser + iOS/Android via Expo Go (tsc 0 errors, expo-doctor 21/21, Metro bundle 3.1 MB) |
| Dead/duplicate source files | 7 | 0 (3 more orphaned API/script files removed with the mobile pass) |

Live browser check (Cursor browser, Sept 16): create pet → attach clip → run →
saved observation opened at `/history/<id>` with factors, raw measurements, and
limitations rendered. Blocking the API produced the reachable-service error in
the UI without a crash.

What this changes for judging: the "AI" claim is now backed by a real pipeline
(OpenCV + optional MoveNet), the score is explainable factor by factor, and the
app cannot show a measurement it did not take.

---

## 4. Team roles

| Member | Role (from the planning doc) | Owns in the code |
| --- | --- | --- |
| **Abhi** | Technical lead, coding, AI integration, debugging, final integration | `artifacts/api-server`, `lib/`, deployment, `gait_engine/movenet.py` |
| **Sudarshan** | Problem-solver, analytical model design, scoring reasoning | `gait_engine/wellness.py`, `gait_engine/features.py` |
| **Kavin** | UI, pseudocode, testing, usability, rubric alignment | `artifacts/silverpaws-beta/src/components`, `pages`, `TESTING.md` |
| **All three** | Research, outreach, information strategy | Survey results, vet/rehab outreach, copy review |

---

## 5. Remaining work by member

Phase 1 (section 9) finished the marked scoring, trend, pet-form, and rewrite
request. The cards below are the September handoff. Still open from this list:
head-bob measurement, a live provider walk-through, the cognitive log, the
accessibility pass, a phone test on a real device, and the copy review.

Each item lists: file, what to do, how to check it. Do not start by rewriting
what already works — extend the marked function or component.

### 5.1 Sudarshan — scoring model

Marked in code with `# TEAM TASK: SUDARSHAN` in `gait_engine/wellness.py`.

**S1. Mobility factor**
File: `gait_engine/wellness.py` → `mobility_factor(measurements)`
Currently returns `None`. Inputs already saved per clip: `hipStability` (0–1),
`leftAnkleMotion`, `rightAnkleMotion`, `strideSymmetry`, `meanKeypointConfidence`.
Decide a 0–100 score. Abhi's original plan used a *penalty* model (start at 100,
subtract for asymmetry and instability) — that is a reasonable starting shape.
Return `None` when the clip has no reliable pose (`symmetryReliable` is false).
Then add `"mobility": <weight>` to `DEFAULT_WEIGHTS`.
Check: `python -m unittest discover -s tests -t .` and add a test in
`tests/test_wellness.py`.

**S2. Historical change factor**
File: `gait_engine/wellness.py` → `historical_change_factor(overall, previous_overall)`
Currently returns `None`. The pipeline already calls it after the overall score
exists and recomputes the overall when a weight is present. Decide how a delta
maps to 0–100 and how a first walk (no baseline) behaves (`None`).
Add `"historicalChange": <weight>` to `DEFAULT_WEIGHTS`.

**S3. Weight calibration**
File: `gait_engine/wellness.py` → `DEFAULT_WEIGHTS`
Current values are engineering placeholders (0.45 / 0.35 / 0.20). Compare them
with the planning doc's QoL formula (mobility 0.40, cognitive 0.35, happiness
0.25) and write down the final reasoning in a comment above the dict.

**S4. Thresholds review**
`CONCERNING_DROP = 10.0`, `CONCERNING_ASYMMETRY = 20.0`. Keep, change, or
justify. These decide when the app tells an owner to ask a vet.

**S5. Optional — head-bob measurement**
File: `gait_engine/features.py`
The planning doc specified nose-Y standard deviation as a front-limb indicator.
It is not implemented. If you want it, add `head_bob_variance(keypoints)` next to
`hip_stability`, add it to `measurements` in `pipeline.py`, and to the OpenAPI
schema (`lib/api-spec/openapi.yaml`, then `pnpm --filter @workspace/api-spec run codegen`).

### 5.2 Kavin — UI, validation, tests

Marked in code with `TEAM TASK: KAVIN` in `trend-panel.tsx` and `pet.tsx`.

**K1. Trend panel**
File: `artifacts/silverpaws-beta/src/components/trend-panel.tsx`
Replace the placeholder body. Show date, overall score, movement consistency,
and symmetry across saved walks. Only compare records with the same `pipeline`
field. Handle 0, 1, and many walks. Use only fields already in `Analysis`
(`createdAt`, `overallScore`, `factors`, `pipeline`). No invented data.
It is already mounted on the History page, so you can see it as you work.

**K2. Pet form validation**
File: `artifacts/silverpaws-beta/src/pages/pet.tsx` → `submit`
Show a visible message when name is blank, or when age/weight is filled in but
is not a positive number. Do not call `addPet`/`updatePet` until checks pass.
Reuse the error style from `analyze.tsx` (`role="alert"`, `text-analysis-error`).

**K3. One automated UI test**
Pick one: blank pet name does not save; non-video file shows
`text-upload-error`; empty history shows the "Record a walk" link. Add the
command to `TESTING.md`.

**K4. Cognitive (DISHAA) quick-tap log — optional but high pitch value**
The planning doc's second "silent condition" (CCD) has no UI yet. This is plain
forms + local storage + weighted sum — no ML. Suggested pieces: a `pages/cognitive.tsx`
with the ten quick-tap symptoms and their weights from the doc, a `cognitiveLogs`
array in `storage.ts`, and a simple per-hour count for the sundowning view.
Coordinate with Sudarshan on the score formula (`weighted_sum / 17.5`, inverted to 0–100).

**K5. Accessibility pass**
Run a screen reader over Analyze and History. Confirm factor bars have text
values (they do) and that "Not scored" tags are announced.

**K6. Phone test run (Expo Go)**
Follow "Mobile checks on a phone" in `TESTING.md` on at least one iPhone and
one Android device. Record which steps passed, clip sizes that worked, and
anything that felt slow. The mobile `TrendPanel` and pet-form messages (K1,
K2) have matching placeholders in `mobile/`.

### 5.3 Abhi — integration and hardening

Marked in code with `// TEAM TASK: ABHI` in `explanation.ts`.

**A1. Language-model rewrite request**
File: `artifacts/api-server/src/lib/explanation.ts` → `requestModelRewrite`
Send `buildExplanationPrompt(context)` to a chat-completions endpoint using
`SILVERPAWS_LLM_URL`, `SILVERPAWS_LLM_KEY`, `SILVERPAWS_LLM_MODEL`. Use an
`AbortSignal` timeout. Return `null` on any error; never throw; never log the key.
Do **not** change `validateExplanation` — it is the safety layer and is tested.
Check: `pnpm --filter @workspace/api-server run test`; then a live clip with the
env vars set should return `usedLlm: true` and the History tag "Model-written summary".

**A2. MoveNet path verification**
This machine only had OpenCV (Python 3.12). Install `requirements.txt` on
Python 3.10/3.11 and run `python scripts/analyze_clip.py <dog clip>`. Confirm
`pipeline: "movenet"` and that `strideSymmetry`/`hipStability` are populated.
Record the result in `TESTING.md`.

**A3. Performance**
`MAX_POSE_FRAMES = 120` reads the *first* 120 frames. Consider evenly sampled
frames for long clips. Measure with a 30–60 s clip.

**A4. Deployment**
`.replit` still targets a single Node process. The API now spawns Python, so
the deploy image needs Python + OpenCV (and TF if pose is wanted). Document the
chosen approach (Nix packages, Docker, or Cloud Run as in the original plan).

**A5. Security review**
Upload path: size cap, temp-file cleanup, filename never used as a path — done.
Review: CORS origin, rate limiting on `/api/analyze`, and what stderr from the
Python process is logged. The API now also serves phones on the LAN; decide
whether it should stay open on `0.0.0.0` or bind to a chosen interface.

**A7. Mobile beyond Expo Go (optional)**
Expo Go allows plain `http://` to the laptop. A TestFlight / Play build would
need a hosted HTTPS API (`EXPO_PUBLIC_API_URL`) or `expo-build-properties`
with a cleartext exception, plus EAS Build configuration.

**A6. Optional — persistence beyond `localStorage`**
`lib/db` is still a stub. If the team wants family sync or the "Silver Passport"
idea from the planning doc, that starts here. Not needed for the submission.

### 5.4 All three — research and copy

- Reconcile the planning doc with the app's language. The doc says "identify
  pain" and "more accurate diagnoses"; the app says "observational, not a
  diagnosis." Pick the app's wording for the pitch.
- Use the owner survey (Section 3) to justify feature priority in the write-up.
- Keep the B2B ideas (vet rehab, foster passport, senior stay) in a
  "future work" section, not in the build.

---

## 6. How to run and verify (short version)

```bash
pnpm install
python -m venv .venv && .venv\Scripts\activate    # macOS/Linux: source .venv/bin/activate
pip install opencv-python numpy

pnpm --filter @workspace/api-server run dev        # :8080
pnpm --filter @workspace/silverpaws-beta run dev   # :4173
```

```bash
pnpm run typecheck
pnpm build
pnpm --filter @workspace/api-server run test
python -m unittest discover -s tests -t .
python scripts/analyze_clip.py path/to/walk.mp4 --pet-name Mabel
```

No API keys are required. Optional variables are listed in `README.md`.

---

## 7. Known limitations to state openly

- MoveNet is a human-pose model; pet limb detections are often low-confidence
  and are reported as "Not measured" rather than guessed
- One short clip from one angle is not a health assessment
- Data is per-browser (`localStorage`); no accounts, no sync
- Cognitive tracking, happiness slider, and the multi-day QoL trend from the
  planning doc are not yet built
- The language-model rewrite is connected when `SILVERPAWS_LLM_URL` and
  `SILVERPAWS_LLM_MODEL` are set. With those unset, the app still shows the
  rule-based observation (`usedLlm: false`). See section 9.

---

## 8. File index of this pass

**Added**
`gait_engine/motion.py`, `gait_engine/features.py`, `gait_engine/wellness.py`,
`gait_engine/pipeline.py`, `scripts/analyze_clip.py`, `tests/__init__.py`,
`tests/test_features.py`, `tests/test_wellness.py`,
`artifacts/api-server/src/routes/analyze.ts`,
`artifacts/api-server/src/lib/{multipart,analysis-runner,explanation}.ts`,
`artifacts/api-server/tests/{multipart,explanation}.test.ts`,
`artifacts/silverpaws-beta/src/lib/analysis-api.ts`, `docs/PROJECT_STATUS.md`

**Modified**
`lib/api-zod/{tsconfig.json,src/index.ts}`, `lib/api-client-react/src/index.ts`,
`artifacts/api-server/{package.json,src/routes/index.ts}`,
`artifacts/silverpaws-beta/{vite.config.ts,src/index.css}`,
`artifacts/silverpaws-beta/src/{App.tsx,pages/analyze.tsx,pages/history.tsx,pages/home.tsx,pages/pet.tsx}`,
`artifacts/silverpaws-beta/src/{lib/storage.ts,lib/report.ts,components/app-shell.tsx,components/trend-panel.tsx,hooks/use-local-data.ts}`,
`gait_engine/__init__.py`, `README.md`, `ARCHITECTURE.md`, `TEAM_TASKS.md`, `TESTING.md`

**Removed**
`artifacts/silverpaws-beta/src/lib/{analyze-client,local-motion-probe,wellness}.ts`,
`gait_engine/{explain,motion_fallback,test_engine}.py`

---

## 9. Phase 1 (October 18, 2026)

Scoring, trends, pet-form checks, and the optional rewrite request. Phases 2–6
were not started.

### What landed

- `mobility_factor` averages measured stride symmetry with hip stability when
  the pose is reliable and both ankle motions were measured. A missing hip is
  left out. A missing ankle, or an unreliable pose, returns `None`.
- `historical_change_factor` is 100 when this walk is at or above the previous
  overall score, drops one point per point of decline, floors at 0, and returns
  `None` on a first walk.
- `DEFAULT_WEIGHTS` now includes `mobility` 0.20 and `historicalChange` 0.10.
  The original consistency / symmetry / activity weights are unchanged.
  `CONCERNING_DROP` stays 10 and `CONCERNING_ASYMMETRY` stays 20.
- Web and phone trend panels list date, overall score, movement consistency,
  and symmetry from saved walks only. Different `pipeline` values are separate
  series. The phone draws the overall scores with `react-native-svg`.
- Pet forms on web and phone show a message for a blank name, and for an age
  or weight that is filled in but is not a positive number. Save does not run
  until those checks pass. The web `/pet` route now renders `PetProfile` as a
  child element. The previous inline `component` function was a new component
  type on every render, so the “Saved locally” note was cleared as soon as the
  profile was written.
- `requestModelRewrite` posts `buildExplanationPrompt` to a chat-completions
  endpoint and aborts after 8 seconds. Any failure returns `null`. The key is
  not logged. `validateExplanation` is unchanged.

### Where this prompt disagreed with the repo

The repo won in each case.

1. **Error style class.** `docs/PROJECT_STATUS.md` section 5.2 said to reuse a
   `text-analysis-error` class. That class is not in the stylesheet. The analyze
   page uses `role="alert"`, the color `#a54339`, and a `data-testid`. Pet
   validation follows that page.
2. **Planning-doc weights.** Section 5.1 compared the score with a QoL formula
   of mobility 0.40, cognitive 0.35, and happiness 0.25. This pipeline does not
   measure cognition or happiness. Those weights were not copied. The three
   existing weights stayed, and mobility plus historical change were added as
   extra relative weights. `overall_score()` already renormalizes over the
   factors a clip actually scored.
3. **Live rewrite walk-through.** `TEAM_TASKS.md` asks for a live clip after
   the rewrite works, recorded in `TESTING.md`. This environment has no
   provider and no sample walk was sent through UI → API → pipeline. Mock
   tests cover the three outcomes (no env, valid rewrite, invalid rewrite).
   The live check stays open.
4. **Weight units.** The prompt did not mention units. The web form labels
   weight in kilograms and the phone form labels it in pounds. Both were left
   as they are.
5. **`react-native-svg` was not installed.** The phone trend view needs it.
   `15.15.4` was added because that is the version Expo SDK 57 pins in
   `bundledNativeModules.json`. The Expo SDK was not upgraded.
6. **History copy.** The factor help text said mobility and change from
   baseline were “Not scored in this release.” That sentence was updated so
   the breakdown matches the scores the pipeline now returns.

### Still open after Phase 1

- Live language-model walk-through (Abhi)
- Head-bob measurement, cognitive log, accessibility pass, and a phone test
  on a real device
- Copy review in the product/research task (`TEAM_TASKS.md`)
- Phases 2–6 were not started in the Phase 1 commit. Phase 2 is recorded below.

---

## 10. Phase 2 (October 18, 2026)

Pose confidence, clip-quality notes, model identity, pinned Python deps, and
a warmed MoveNet cache. Phase 3 was not started.

### What landed

- Pose frames are summarized as `modelConfidence` (0–1), `framesUsed`, and
  `framesTotal`. Below the existing 0.3 mean, limb measurements stay unset and
  `lowConfidence` is true. Web history and the phone result screens show
  **Low confidence — try a clearer clip**. A missing confidence is not shown
  as zero.
- `modelInfo` names the pipeline, model, version, and `runsOn: "server"`.
  MoveNet Thunder stays primary. OpenCV frame difference stays the fallback.
  A non-Thunder URL is not labeled as Thunder.
- `qualityNotes` covers a short clip, a long clip, a tiny frame, a dark or
  blown-out frame, and a clip with little movement. Unknown duration is not
  described as 0 seconds.
- `requirements.txt` and `requirements-opencv.txt` pin versions. TensorFlow
  stays on Python 3.10–3.11. `scripts/cache_movenet.py` fills `models/tfhub`
  so a deploy can warm the weights before the first request.
- `docs/MODEL_CARD.md` records intended use, the human-training limit, failure
  modes, and measured versus interpreted values.
- `tests/upload-cleanup.test.ts` posts a clip and checks the upload directory
  is empty afterward. Python tests: 54 passed. API tests: 23 passed.

### Where this prompt disagreed with the repo

1. **`confidence` is already 0–100.** The prompt asks for `modelConfidence`
   from 0 to 1. Both are returned. `confidence` stays the percent so the
   existing history grid and PDF do not change meaning. `modelConfidence` is
   the 0–1 value.
2. **Thresholds already existed.** Per-keypoint gating is 0.2 and the mean
   trust line is 0.3 (`POSE_CONFIDENCE_THRESHOLD`, `MIN_POSE_CONFIDENCE`).
   Those were reused instead of adding a third cutoff.
3. **Dependencies were already pinned** in `requirements.txt`. A separate
   `requirements-opencv.txt` now pins the fallback install, which the README
   previously installed without versions.
4. **There is no deploy image yet** (that is a later phase). The weight cache
   is a script plus `TFHUB_CACHE_DIR`, not a Docker build step. If the script
   was not run and TensorFlow is installed, the first pose request still
   downloads Thunder once. The fallback path never downloads it.
5. **Quality notes do not reject the HTTP request** when the clip can still
   be measured. Unreadable files stay a 400. The prompt asked for messages
   the owner can act on; those messages travel on the result.

---

## 11. Phase 3 (October 18, 2026)

Phone features around the existing screens. Phase 4 was not started.

### What landed

- Onboarding has three steps. Analysis stays locked until the owner
  acknowledges "this is a wellness note, not a diagnosis". That flag is stored
  on the phone.
- The Analyze screen lists the filming guide, a connection chip for
  `/api/healthz` that retries with backoff, and the privacy line. A failed
  analysis keeps the chosen clip and offers Try again.
- Demo mode shows one bundled sample labeled "Sample data — not your pet".
  `addAnalysis` drops it, history helpers drop it, and it is not included in
  trends or the vet summary.
- History filters by pet and clears a filter if that pet was deleted. Compare
  refuses two walks whose pipelines differ.
- A walk can be shared as a PDF. A vet summary covers the latest saved walks,
  grouped by pipeline, with the veterinarian pointer only when a change is
  concerning. The PDF footer says the AI-use list arrives with the registry.
- Settings adds kg/lb for new pets, theme, a weekly local reminder (permission
  asked when the switch is turned on), an Advanced API address toggle around
  the existing editor, JSON export, feedback without a video, version, and a
  short How AI is used placeholder.
- Shared controls use 44 pt targets, selected chips include a check mark, and
  a root error boundary catches a thrown screen. History and Analyze show a
  loading state.

### Where this prompt disagreed with the repo

1. **Clip length.** The filming guide recommends 5–15 seconds. The existing
   Analyze copy and the API still allow up to 120 seconds. The guide was
   added; the limit was not tightened.
2. **Weight units.** New pets default to kg, matching the web form. A phone
   profile saved before this change has no stored unit, so it stays labeled
   lb. Changing the unit does not convert the number.
3. **API address.** Settings already showed the address to every tester. It
   now sits behind an Advanced switch. The editor itself was not removed.
4. **Dark theme.** Navigation, cards, buttons, and notes follow the choice.
   Some screen stylesheets still carry the original light-palette text color,
   so a few labels do not recolor. That is unfinished polish, not a second
   theme system.
5. **No phone or simulator was available here.** Checks are typecheck and
   unit tests. Expo Go, local notifications, and the PDF share sheet were
   not run on a device.

The Phase 3 gaps above (dark-mode text colors, no unit conversion for older
profiles, filming-guide 5–15 seconds versus the API's 120 second limit) are
unchanged.

---

## 12. Phase 4 (October 18, 2026)

One AI-use registry. Phase 5 was not started.

### What landed

- `lib/ai-use/registry.json` is the only wording source. `scripts/sync-ai-use.mjs`
  copies it into the web app and `mobile/src/lib/`, and writes `docs/AI_USE.md`.
- A clip's `aiUse` lists the steps that ran. MoveNet runs include `pose-model`.
  Every successful clip includes `motion-fallback`, because OpenCV frame
  difference always runs. `scoring` and `observation-rules` are always included.
  `llm-rewrite` is added by the API only when a validated rewrite is kept.
  `development` is never attached to a clip.
- Result screens and both PDFs show one registry `resultLine` per id. Settings
  → How AI is used (and the web AI-use page) show the summary and the full
  list, including development.

### Where this prompt disagreed with the repo

The suggested MoveNet id list was pose-model, scoring, and observation-rules.
`gait_engine/pipeline.py` calls `read_motion_signal` before it tries pose, and
movement consistency and activity come from that signal even when MoveNet
succeeds. `motion-fallback` is therefore included on pose runs as well. Its
registry text says it runs on every clip, not only when pose is missing.

The Phase 3 gaps (dark-mode label colors, no unit conversion for older
profiles, filming-guide 5–15 seconds versus the API's 120 second limit) are
still open. Phase 5 does not change them.

---

## 13. Phase 5 (October 18, 2026)

Hosting config and an Expo tester guide. Phase 6 was not started. No deploy
and no Expo build were run. There is no public URL and no store listing.

### What landed

- `Dockerfile` and `docker-compose.yml` for the API and the Python pipeline.
  The image is Node 20 and Debian bookworm Python 3.11, with
  `opencv-python-headless`, NumPy, TensorFlow, and a MoveNet cache filled by
  `scripts/cache_movenet.py` at image build time.
- Production requests other than `/api/healthz` require HTTPS. Uploads stay
  capped (`MAX_UPLOAD_MB`, default 60). Analysis stops after
  `ANALYSIS_TIMEOUT_MS` (default 120000). Each client address gets a small
  per-minute analysis limit.
- `docs/HOSTING.md` lists the environment variables, starts RAM at 2 GB, and
  says how to read a real peak. The host steps are for Render. The service
  was not created.
- `mobile/app.config.ts` reads `EXPO_PUBLIC_API_URL`. Development still guesses
  the laptop. A release build does not. Settings → Advanced remains the tester
  override.
- `mobile/eas.json` has `development`, `preview` (internal), and `production`,
  each with its own update channel. The bundle id `com.silverpaws.app` is a
  placeholder. The previous id was `org.silverpaws.mobile`.
- Camera and photo-library strings say what is measured. Microphone permission
  is turned off (`microphonePermission: false`) because the pipeline never
  reads sound.
- `docs/EXPO_TESTING.md` is the tester guide. Commands were checked against
  docs.expo.dev for EAS Build, internal distribution, and EAS Update.

### Docker

The `docker` command is not installed in this environment, so the image was
**not** built. About 246 GB of disk was free. Available RAM was about 4.6 GB,
which is tight for a TensorFlow image build even if Docker were present.
Do not treat the Dockerfile as a finished image.

### Where this prompt disagreed with the repo

1. **OpenCV wheel.** `requirements.txt` pins `opencv-python` for a laptop with
   a display. The image uses `opencv-python-headless` at the same version
   (`4.10.0.84`) because the container has no screen.
2. **Bundle id.** The repo had `org.silverpaws.mobile`. Phase 5 sets the
   placeholder `com.silverpaws.app` and flags it for a human to replace.
3. **Icons.** `attached_assets/` has no images. `mobile/assets/` already holds
   the Expo template icon and splash. They were left in place and flagged.
   No new artwork was invented.
4. **Updates URL.** `eas update:configure` writes the Expo project id and
   `updates.url` after a person logs in. Those values are not in the repo,
   because inventing a project id would be a fake deploy. `docs/EXPO_TESTING.md`
   tells the human to run that command before the first preview build.
5. **Expo patch pins.** `npx expo-doctor` failed on the previous SDK 57 patch
   pins (`expo` 57.0.23 and three related packages). They were moved to the
   versions doctor asked for (`expo` ~57.0.30 and matching patches). The SDK
   stayed 57. The legacy `splash` field is not allowed, so the placeholder
   splash image is set with the `expo-splash-screen` plugin instead.

---

## 14. Phase 6 (October 18, 2026)

The three Phase 3 gaps are closed. No deploy, no `eas build`, and no login.
The testing record is in `TESTING.md`.

### What changed

- Dark mode: labels on Home, Analyze, History, the walk detail, the pet form,
  Settings, trends, and the error screen take their text color from the active
  palette. The surfaces those labels sit on do too. A missing score is the
  words "Not scored" or "Not measured", and a selected chip includes a check
  mark, so meaning is not color alone.
- Units: an older phone profile with no stored unit stays labeled pounds.
  Switching kg/lb converts the number and shows both values ("62 lb is now
  28.1 kg"). A value that is not a positive number is not relabeled. New pets
  still default to kilograms. The web form still says kilograms only, because
  that form never stored a separate unit.
- Filming: the phone guide, the web upload line, the client errors, and the
  pipeline notes say a useful walk is about 5 to 15 seconds and that the
  server accepts a longer clip up to 120 seconds. The cap in code is still 120.

### Where this prompt disagreed with the repo

There is no walking clip in the repository, and TensorFlow is not installed,
so MoveNet was not run. OpenCV ran on a generated rectangle, recorded in
`TESTING.md` as not a real walk. There is no lint script. GitHub reported no
checks on the pull request. The product/research card and Abhi's live provider
walk-through stay open in `TEAM_TASKS.md`.

A later browser pass on the web app is recorded in `TESTING.md`. The web pet
form still says kilograms. The web app still has no demo mode and no theme
control.
