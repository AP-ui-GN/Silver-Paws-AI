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
- Computer vision pipeline: frames → picture motion, and MoveNet pose when
  TensorFlow is installed
- Gait measurements (left/right ankle motion, stride symmetry) kept separate
  from interpretation
- Transparent factor scores (consistency, symmetry, activity) blended into an
  overall 0–100 indicator
- Rule-based observation text that only quotes measured values
- Optional language-model rewrite (not wired yet — see `TEAM_TASKS.md`)
- History of saved observations, PDF report, and a veterinarian prompt when
  a change looks concerning

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
| Database (future) | `lib/db` (schema stub only; beta uses `localStorage`) |

Human-facing code (routing, forms, storage, charts) stays in the frontend.
Pose detection, feature math, scoring, and explanation live behind the API.

## AI components

- **MoveNet Thunder** (TensorFlow Hub) for 17-point pose landmarks, when
  TensorFlow is available. This model was trained on human bodies, so pet
  detections can be unreliable; low confidence is reported as “not measured”
  rather than treated as a perfect score.
- **OpenCV motion fallback** when TensorFlow is missing: frame-to-frame
  picture change. The result is labeled `opencv-motion` so it is never mixed
  with pose-based scores.
- **Rule-based observation** in `gait_engine/wellness.py`.
- **Optional LLM rewrite** in `artifacts/api-server/src/lib/explanation.ts`.
  Invalid rewrites are rejected; the rule-based text is shown instead.

## Limitations

- Does not diagnose injury, pain, or disease
- Does not replace a veterinarian
- Not for emergencies
- One camera angle of one short clip is not a full picture of a pet
- MoveNet is a human-pose model; treat pet limb detections cautiously
- Beta data stays in this browser (`localStorage`), not a shared database

## How to run

Needs **Node.js 20+**, **pnpm**, and **Python 3.10–3.12** with OpenCV.

```bash
pnpm install
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install opencv-python numpy
```

For pose landmarks as well (Python 3.10 or 3.11):

```bash
pip install -r requirements.txt
```

Start both services (two terminals):

```bash
# terminal 1 — analysis API (port 8080)
pnpm --filter @workspace/api-server run dev

# terminal 2 — app (port 4173), proxies /api to the server
pnpm --filter @workspace/silverpaws-beta run dev
```

Open http://127.0.0.1:4173

### On a phone (Expo Go)

With the API from terminal 1 still running:

```bash
cd mobile
npm install
npm start
```

Scan the QR code with Expo Go on a phone on the same Wi-Fi. The app finds the
API on the laptop automatically; `mobile/README.md` covers the manual address
and tunnel options.

Optional environment variables:

| Variable | Where | Default | Purpose |
| --- | --- | --- | --- |
| `PORT` | API / Vite | `8080` / `4173` | Listen port |
| `BASE_PATH` | Vite | `/` | Public path prefix |
| `API_PROXY_TARGET` | Vite | `http://127.0.0.1:8080` | Dev proxy for `/api` |
| `SILVERPAWS_PYTHON` | API | project `.venv` if present | Python used to run the pipeline |
| `SILVERPAWS_REPO_ROOT` | API | inferred | Repo root so the CLI can be found |
| `MAX_UPLOAD_MB` | API | `60` | Upload size cap |
| `ANALYSIS_TIMEOUT_MS` | API | `120000` | Pipeline timeout |
| `SILVERPAWS_LLM_URL` | API | unset | Optional rewrite endpoint (Abhi) |
| `SILVERPAWS_LLM_KEY` | API | unset | Bearer token (Abhi) |
| `SILVERPAWS_LLM_MODEL` | API | unset | Model name (Abhi) |
| `EXPO_PUBLIC_API_URL` | mobile | derived from the Expo dev server | API address baked into the phone app |

No API keys are required for the app to analyze a clip.

## How teammates can contribute

Read `TEAM_TASKS.md`. Each unfinished task points at one file and lists
completion criteria. Do not rewrite working UI or pipeline code to start a
task — extend the function or component that is already marked.

## Documentation

- `ARCHITECTURE.md` — data flow and module boundaries
- `TEAM_TASKS.md` — Sudarshan, Kavin, and Abhi work
- `TESTING.md` — how to verify the app
- `docs/PROJECT_STATUS.md` — what changed, measured impact, per-member handoff
- `mobile/README.md` — running the phone app in Expo Go
