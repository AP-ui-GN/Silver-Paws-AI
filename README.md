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

- Pet profile (name, species, breed, age, weight, notes) stored in this browser
- Walking-clip upload with file, size, and duration checks
- Computer vision pipeline: frame-to-frame picture motion on every clip, plus
  RT-DETR dog detection/tracking and QuadPose F2's 17 AP-10K-order animal
  landmarks when the full dependencies and checksum-verified weights are installed
- Measurements kept separate from interpretation. Gait calculations and
  thresholds are experimental and have not been validated on a labeled set of
  pet-dog walking clips; unavailable values remain “Not measured”
- Transparent factor scores (consistency, symmetry, mobility, activity, and
  change from the previous walk) blended into an overall 0–100 indicator
- Rule-based observation text that only quotes measured values
- Optional language-model rewrite when `SILVERPAWS_LLM_URL` and
  `SILVERPAWS_LLM_MODEL` are set; otherwise the rule-based note is shown. After
  three consecutive provider failures, rewrites cool down for 30 seconds while
  the rule-based note continues to work.
- History of saved observations, PDF report, and a veterinarian prompt when
  a change looks concerning

## Architecture

```text
Web UI (React)  →  API (Express)  →  Python pipeline (gait_engine)
                         ↓
                   localStorage  →  dashboard / history
```

| Layer | Location |
| --- | --- |
| Web frontend | `artifacts/silverpaws-beta` |
| API | `artifacts/api-server` |
| Shared contracts | `lib/api-spec`, `lib/api-zod`, `lib/api-client-react` |
| Analysis / CV | `gait_engine/` |
| Database (future) | `lib/db` (schema stub only; beta uses `localStorage`) |

Human-facing code (routing, forms, storage, charts) stays in the frontend.
Pose detection, feature math, scoring, and explanation live behind the API.

## AI components

The wording for each step lives in `lib/ai-use/registry.json` and is copied
into the web app by `node scripts/sync-ai-use.mjs`. The generated page is
`docs/AI_USE.md`. Pose limits are in `docs/MODEL_CARD.md`.

- **RT-DETR** detects dogs and the tracking layer preserves the selected
  target. **QuadPose F2** returns 17 AP-10K-order animal landmarks inside that
  tracked box. Its checkpoint is pinned and checksum-verified during setup.
  The application's gait formulas and cutoffs are experimental and have not
  been validated on a labeled set of pet-dog walking clips. Heatmap peak scores
  are not calibrated probabilities; unsupported or low-confidence values remain
  “Not measured.”
- **OpenCV frame difference** runs on every clip. It is not a learned model.
  When pose is missing, it is the only movement measurement. When pose runs,
  it still supplies movement consistency and activity. Results from different
  pipelines are never mixed in a chart.
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
- The integrated QuadPose F2/AP-10K pipeline has not been validated on a
  labeled set of pet-dog walking clips. Upstream model benchmarks are not
  SilverPaws end-to-end accuracy claims. See `docs/MODEL_CARD.md` and
  `docs/GAIT_METRICS.md`
- Beta data stays in this browser (`localStorage`), not a shared database

## How to run

Needs **Node.js 24 LTS**, **pnpm 10.33.4**, and **Python 3.10–3.12** with OpenCV.

```bash
pnpm install
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-opencv.txt
```

`requirements-opencv.txt` pins OpenCV and NumPy for Python 3.10–3.12. That
path measures picture motion only and labels the result `opencv-motion`.

For the full dog-pose pipeline, install the CPU detector stack plus ONNX
Runtime (Python 3.10–3.12), then explicitly cache both model assets:

```bash
pip install -r requirements.txt
python scripts/cache_models.py
```

See `docs/MODEL_CARD.md` for what each model is and what it cannot do.

One clip, without the API:

```bash
python scripts/analyze_clip.py path/to/walk.mp4 --pet-name Mabel
python scripts/analyze_clip.py path/to/walk.mp4 --no-pose
python scripts/check_pose_backend.py path/to/walk.mp4 --out outputs/pose-check/
```

`--no-pose` keeps the OpenCV motion result. Pose-review output uses the
QuadPose F2 AP-10K landmark order. Do not commit the clip or `outputs/`.

Tests:

```bash
python -m unittest discover -s tests -t .
pnpm --filter @workspace/api-server run test
pnpm --filter @workspace/silverpaws-beta run test
```

Recorded on October 22, 2026 after the tracker and upload-limit changes:
90 Python tests, 45 API tests, and 17 web tests passed, with API and web
typechecks passing. The hosted workflow also passed its Python, API, and web
jobs. These are point-in-time checks; they do not validate canine pose accuracy.

Start both services (two terminals):

```bash
# terminal 1 — analysis API (port 8080)
pnpm --filter @workspace/api-server run dev

# terminal 2 — app (port 4173), proxies /api to the server
pnpm --filter @workspace/silverpaws-beta run dev
```

Open http://127.0.0.1:4173

To run the API in Docker, see `docs/HOSTING.md`. GitHub Actions now builds
the image and smoke-tests readiness plus `POST /api/analyze` with a synthetic
motion clip. This verifies container packaging and API integration, not canine
pose accuracy or production-host memory use.

### On a phone on the same Wi-Fi

The web dev script already uses `--host 0.0.0.0`. With both services running,
a phone on the same network can open `http://<laptop-ip>:4173`. Use **Record
walk** on the Analyze page to hand the clip to the phone camera through the
file picker. The page does not open the camera itself.

Optional environment variables:

| Variable | Where | Default | Purpose |
| --- | --- | --- | --- |
| `PORT` | API / Vite | `8080` / `4173` | Listen port |
| `BASE_PATH` | Vite | `/` | Public path prefix |
| `API_PROXY_TARGET` | Vite | `http://127.0.0.1:8080` | Dev proxy for `/api` |
| `SILVERPAWS_PYTHON` | API | project `.venv` if present | Python used to run the pipeline |
| `HF_HOME` | API / Python | `models/hf` by default | RT-DETR detector cache |
| `SILVERPAWS_QUADPOSE_CACHE` | Python | `models/quadpose/quadpose_f2.onnx` | Optional override for the checksum-verified QuadPose checkpoint |
| `SILVERPAWS_REPO_ROOT` | API | inferred | Repo root so the CLI can be found |
| `MAX_UPLOAD_MB` | API | `60` | Upload size cap |
| `ALLOWED_ORIGINS` | API | localhost Vite origins outside production; empty in production | Comma-separated exact browser origins for the deployed web app |
| `ANALYSIS_TIMEOUT_MS` | API | `600000` | Stop the pipeline after this many milliseconds; valid values are 1 second to 1 hour. Motion saved before pose is returned if pose is still running |
| `SHUTDOWN_TIMEOUT_MS` | API | `15000` | Grace period for active requests when the server receives SIGTERM/SIGINT |
| `ANALYZE_MAX_CONCURRENT` | API | `1` | Pipelines running at once. CPU pose inference defaults to one process to limit memory pressure; extra uploads are refused before the body is read |
| `TRUST_PROXY` | API | unset | Set to `1` only behind a proxy that sets `X-Forwarded-Proto` |
| `SILVERPAWS_LLM_URL` | API | unset | Optional chat-completions endpoint |
| `SILVERPAWS_LLM_KEY` | API | unset | Bearer token for that endpoint; never logged |
| `SILVERPAWS_LLM_MODEL` | API | unset | Model name. Required, with the URL, before a rewrite is attempted |

No API keys are required for the app to analyze a clip.

For local CORS defaults and production browser-origin configuration, see
`.env.example` and `docs/HOSTING.md`. In production, set `ALLOWED_ORIGINS`
to the exact HTTPS origin(s) of the web app. CORS is not authentication.

## How teammates can contribute

Read `TEAM_TASKS.md`. Each unfinished task points at one file and lists
completion criteria. Do not rewrite working UI or pipeline code to start a
task — extend the function or component that is already marked.

## Documentation

- `ARCHITECTURE.md` — data flow and module boundaries
- `TEAM_TASKS.md` — Sudarshan, Kavin, and Abhi work
- `TESTING.md` — how to verify the app
- `docs/PROJECT_STATUS.md` — what changed, measured impact, per-member handoff
