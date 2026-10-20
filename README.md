# SilverPaws AI

SilverPaws AI helps pet owners notice observable changes in how a companion
walks. You save a pet profile, upload a short clip, and the app returns
**measured movement values**, **factor scores you can read**, and a
**plain-language note**. It is a wellness observation tool, not a veterinary
diagnosis.

## Problem

Owners often notice “something looks different” on walks but have no record of
what changed. SilverPaws turns a short video into a dated note they can compare
over time and, if needed, take to a veterinarian.

## Major features

- Pet profile (name, species, breed, age, weight, notes) stored in this
  browser, or on the phone. A blank name cannot be saved. Age and weight are
  optional; when they are filled in, they have to be a positive number.
- Walking-clip upload with file, size, and duration checks. A useful walk is
  about 5 to 15 seconds. The server accepts a longer clip, up to 120 seconds
  and 60 MB. The phone can record a clip or choose one from the library.
- Filming guidance: side angle, flat ground, whole body in frame, enough light
  to see the legs. The phone Analyze screen lists those points. The web upload
  page states the same advice in one line.
- Computer vision pipeline: frames → picture motion, and MoveNet pose when
  TensorFlow is installed
- Gait measurements (left/right ankle motion, stride symmetry) kept separate
  from interpretation
- Factor scores for movement consistency, stride symmetry, mobility, activity,
  and change from the previous walk measured the same way. Mobility is scored
  when the pose is reliable and both ankle motions were measured. Change from
  the previous walk is unset on a first walk. A missing factor is “Not scored”,
  never zero. The scored factors blend into an overall 0–100 indicator.
- Rule-based observation text that only quotes measured values
- Optional language-model rewrite of that note when `SILVERPAWS_LLM_URL` and
  `SILVERPAWS_LLM_MODEL` are set. The numbers stay the same. An invalid rewrite
  is discarded and the rule-based note is shown.
- Pose confidence and clip-quality checks. A low-confidence pose shows
  **Low confidence — try a clearer clip**, and limb values stay unset. Quality
  notes cover a short, long, tiny, dark, blown-out, or mostly still clip.
- History of saved observations, and a trend comparison of walks that share a
  pipeline (`movenet` or `opencv-motion`): date, overall score, movement
  consistency, and symmetry
- Web: a PDF of one saved walk, and a veterinarian prompt when a change looks
  concerning. The prompt asks the owner to talk to a professional. It is not a
  diagnosis.
- Phone compare: two saved walks, side by side, only when they used the same
  pipeline. Sample data is refused.
- Phone PDF and veterinarian summary: one walk can be shared as a PDF. The
  summary covers the latest saved walks, grouped by pipeline, and includes the
  veterinarian pointer only when a change is concerning. Sample data is left
  out.
- Phone onboarding: three notes before the first analysis. Analysis stays
  locked until the owner acknowledges that this is a wellness note, not a
  diagnosis.
- Phone connection check. Analyze shows whether the analysis server answered
  `/api/healthz`. While it is offline, the check retries with backoff. A failed
  analysis keeps the chosen clip and offers Try again.
- Phone demo mode: one bundled sample labeled “Sample data — not your pet”.
  It is not saved to history, and it is left out of trends and the veterinarian
  summary.
- Phone settings: kilograms or pounds for a new pet, light / dark / system
  theme, a weekly local reminder (Sunday at 10:00; permission is asked when
  the switch is turned on; not a medical reminder), an Advanced API address,
  JSON export, feedback that does not attach a video, the app version, and
  How AI is used
- AI-use disclosure. Each saved result lists the steps that ran on that clip.
  The web page `/ai-use` and phone Settings → How AI is used show the full
  list, including development assistance. That development note is not a step
  that runs on a clip.

## Architecture

```text
Web UI (React)     ─┐
                    ├→  API (Express)  →  Python pipeline (gait_engine)
Mobile (Expo Go)   ─┘          ↓
                     localStorage / AsyncStorage  →  dashboard / history
```

| Layer | Location |
| --- | --- |
| Web frontend | `artifacts/silverpaws-beta` |
| Mobile app (Expo Go) | `mobile/` — see `mobile/README.md` |
| API | `artifacts/api-server` |
| Shared contracts | `lib/api-spec`, `lib/api-zod`, `lib/api-client-react` |
| Analysis / CV | `gait_engine/` |
| AI-use wording | `lib/ai-use/registry.json` |
| Database (future) | `lib/db` (schema stub only; beta uses `localStorage`) |

Human-facing code (routing, forms, storage, charts) stays in the frontend.
Pose detection, feature math, scoring, and explanation live behind the API.

## AI components

The wording for each step lives in `lib/ai-use/registry.json` and is copied
into the apps by `node scripts/sync-ai-use.mjs`. The generated page is
`docs/AI_USE.md`. Pose limits, versions, and training limits are in
`docs/MODEL_CARD.md`. Those two docs are the source for training provenance
and model metadata.

- **MoveNet Thunder** is Google's single-pose model, TensorFlow Hub
  `movenet/singlepose/thunder/4` (version 4). Input is 256×256. It returns 17
  body keypoints. The analysis server runs it when TensorFlow is installed.
  The phone and the browser only upload the clip. `modelInfo.runsOn` is
  `"server"`, and the result pipeline is `movenet`. It was trained on human
  bodies. SilverPaws did not train it and does not ship a pet dataset, sample
  counts, or training metrics. A dog or cat is outside that training set. Low
  confidence is reported as “not measured”, not as a perfect score. A different
  model URL is not labeled Thunder.
- **OpenCV frame difference** runs on every clip. It is not a learned model.
  When MoveNet is missing, the result pipeline is `opencv-motion` and this is
  the only movement measurement. When MoveNet runs, it still supplies movement
  consistency and activity. Results from the two pipelines are never mixed in
  a chart.
- **Scores and the note** come from fixed formulas and templates in
  `gait_engine/wellness.py`. They are not an AI model.
- **Optional language-model rewrite** in
  `artifacts/api-server/src/lib/explanation.ts`, only when
  `SILVERPAWS_LLM_URL` and `SILVERPAWS_LLM_MODEL` are set. Invalid rewrites
  are discarded. The rule-based note is shown instead.
- **Development.** Parts of this app's code and documentation were written
  with AI coding assistants and reviewed by the team. That fact is not a step
  that runs on a clip.

## Limitations

- Does not diagnose injury, pain, or disease
- Does not replace a veterinarian
- Not for emergencies
- One camera angle of one short clip is not a full picture of a pet
- MoveNet is a human-pose model; treat pet limb detections cautiously
- Beta data stays in this browser (`localStorage`) or on the phone
  (AsyncStorage), not a shared database
- The phone reminder is a filming nudge, not a medical alert
- Demo mode is a labeled sample, not a walk that was measured

## How to run

Needs **Node.js 20+**, **pnpm**, and **Python 3.10–3.12** with OpenCV.

```bash
pnpm install
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-opencv.txt
```

`requirements-opencv.txt` pins OpenCV and NumPy for Python 3.10–3.12. That
path measures picture motion only and labels the result `opencv-motion`.

For pose landmarks, use Python 3.10 or 3.11 (TensorFlow 2.15 does not support
3.12) and warm the model cache so the first request does not download it:

```bash
pip install -r requirements.txt
python scripts/cache_movenet.py
```

See `docs/MODEL_CARD.md` for the pinned versions, what each model is, and what
it cannot do. See `docs/AI_USE.md` for the step-by-step disclosure.

Start both services (two terminals):

```bash
# terminal 1 — analysis API (port 8080)
pnpm --filter @workspace/api-server run dev

# terminal 2 — app (port 4173), proxies /api to the server
pnpm --filter @workspace/silverpaws-beta run dev
```

Open http://127.0.0.1:4173

To run the API in Docker, see `docs/HOSTING.md`. From the repository root,
when Docker is installed: `docker compose up --build`, then open
http://127.0.0.1:8080/api/healthz. The image was not built in this repository
checkout. In production, paths other than `/api/healthz` require HTTPS.

### On a phone (Expo Go)

With the API from terminal 1 still running:

```bash
cd mobile
npm install
npm start
```

Scan the QR code with Expo Go on a phone on the same Wi-Fi. The first launch
shows three short notes. Analysis stays locked until you acknowledge that this
is a wellness note, not a diagnosis. The app finds the API on the laptop
automatically. If that guess is wrong, Settings → Advanced has the address and
a connection test. `mobile/README.md` covers the tunnel option.

A shared preview build is separate from Expo Go. The steps, with no install
link in this repository, are in `docs/EXPO_TESTING.md`.

Optional environment variables:

| Variable | Where | Default | Purpose |
| --- | --- | --- | --- |
| `PORT` | API / Vite | `8080` / `4173` | Listen port |
| `BASE_PATH` | Vite | `/` | Public path prefix |
| `API_PROXY_TARGET` | Vite | `http://127.0.0.1:8080` | Dev proxy for `/api` |
| `NODE_ENV` | API | unset | `production` requires HTTPS except on `/api/healthz` |
| `SILVERPAWS_PYTHON` | API | project `.venv` if present | Python used to run the pipeline |
| `SILVERPAWS_REPO_ROOT` | API | inferred | Repo root so the CLI can be found |
| `SILVERPAWS_MOVENET_CACHE` | API | `models/tfhub` | MoveNet weight cache filled by `scripts/cache_movenet.py` |
| `MAX_UPLOAD_MB` | API | `60` | Upload size cap |
| `ANALYSIS_TIMEOUT_MS` | API | `120000` | Pipeline timeout |
| `ANALYZE_RATE_LIMIT_PER_MINUTE` | API | `10` | Analyses allowed per client address each minute |
| `SILVERPAWS_LLM_URL` | API | unset | Optional chat-completions endpoint |
| `SILVERPAWS_LLM_KEY` | API | unset | Bearer token for that endpoint; never logged |
| `SILVERPAWS_LLM_MODEL` | API | unset | Model name. Required, with the URL, before a rewrite is attempted |
| `EXPO_PUBLIC_API_URL` | mobile | derived from the Expo dev server | API address baked into a release build. Development still guesses the laptop |

No API keys are required for the app to analyze a clip. Host memory and the
Render steps are in `docs/HOSTING.md`.

## How teammates can contribute

Read `TEAM_TASKS.md`. Each unfinished task points at one file and lists
completion criteria. Do not rewrite working UI or pipeline code to start a
task — extend the function or component that is already marked.

## Documentation

- `ARCHITECTURE.md` — data flow and module boundaries
- `TEAM_TASKS.md` — Sudarshan, Kavin, and Abhi work
- `TESTING.md` — how to verify the app
- `docs/PROJECT_STATUS.md` — what changed, measured impact, per-member handoff
- `docs/MODEL_CARD.md` — MoveNet Thunder and OpenCV: name, version, where it
  runs, human-training limits, confidence, and failure modes
- `docs/AI_USE.md` — generated disclosure of each step (from
  `lib/ai-use/registry.json`)
- `docs/HOSTING.md` — Docker image and host steps for the analysis API
- `docs/EXPO_TESTING.md` — preview builds for phone testers
- `mobile/README.md` — running the phone app in Expo Go
