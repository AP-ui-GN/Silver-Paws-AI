# Testing guide

## Automated checks (verified)

From the workspace root, with the project `.venv` activated for Python:

```bash
pnpm run typecheck
pnpm build
pnpm --filter @workspace/api-server run test
python -m unittest discover -s tests -t .
```

What those cover:

- TypeScript across libs, API, and the app
- Production builds of the API and the frontend
- Multipart parsing and explanation validation, including a mock language-model
  provider (35 Node tests as of October 18, 2026)
- Motion statistics, consistency, hip stability, symmetry, mobility,
  historical change, observation text, confidence gating, and clip-quality
  notes (55 Python tests as of October 18, 2026)
- Uploaded clips are deleted after `POST /api/analyze`, including when the
  file is rejected (`tests/upload-cleanup.test.ts`)
- Pet-form validation and trend grouping, from the web package:

```bash
pnpm --filter @workspace/silverpaws-beta run test
```

Standalone pipeline (no API):

```bash
python scripts/analyze_clip.py path/to/walk.mp4 --pet-name Mabel
```

Add `--no-pose` to force the OpenCV-only path.

Mobile app (from `mobile/`):

```bash
npm run typecheck        # tsc, 0 errors
npm run doctor           # expo-doctor, 21/21 checks
npm run export:check     # Metro bundle without a device
```

## Mobile checks on a phone (Expo Go)

Not run in this pass — no phone was attached. Run with the API server up and
`npm start` in `mobile/`:

1. Scan the QR code; the Home tab loads with the "Add your first pet" card.
2. Settings → **Test connection** reports "Connected" with the laptop's address.
   If not, type `<laptop-ip>:8080`, Save, and test again.
3. Create a pet; you land on Analyze with that pet selected.
4. **Choose video** with a non-video file (Android lets you) → the red note
   says to choose a video. Nothing uploads.
5. **Record** a 5–10 s side-on walk → upload percentage climbs, then
   "Measuring movement…", then the saved card with a score and observation.
6. Tap **See the full breakdown** → factors, raw measurements grid, limitations.
7. Stop the API server, analyze again → "Could not reach the analysis
   service…" with no crash; Cancel works mid-upload.
8. Kill and reopen the app → pets and walks are still there (AsyncStorage).

## Live product checks (verified in this pass)

Both services running:

```bash
pnpm --filter @workspace/api-server run dev
pnpm --filter @workspace/silverpaws-beta run dev
```

### Pet profile

- Create a pet named Mabel and save — profile appears in the device list
- Data is in `localStorage` key `silverpaws:pets`

### New analysis

- Choose a short MP4 and review it
- Run analysis — processing stage, then history detail
- Result includes overall score, factor breakdown, raw measurements, and
  limitations (not a diagnosis)
- Non-video upload to `/api/analyze` returns 400
- Missing file returns 400 “Choose a video file…”
- Corrupt `.mp4` returns 400 “could not be opened as a video”

### History and report

- Detail page separates **raw measurements** from **interpretation**
- PDF contains those sections in that order, plus source/license fallbacks
  and “not a medical diagnosis”

### Safety

- Footer shows the disclaimer and emergency note on every page
- A large drop vs the previous walk, or reliable high asymmetry, sets
  `concerningChange` and tells the owner to ask a veterinarian

## What to test

On a saved result, the AI-use lines should name only the steps that produced that walk: MoveNet when pose ran, frame-to-frame motion (it runs on every clip), fixed scores and a fixed note, and a language-model reword only when the server kept one.

## Manual checklist (for teammates)

- [ ] Create and edit a second pet
- [ ] Reject a huge file in the UI before upload
- [ ] Run two clips for the same pet and confirm the second observation
      mentions the score difference
- [ ] Delete an observation and visit its old URL
- [ ] Stop the API and confirm the analyze page shows a reachable-service error
- [ ] Confirm MoveNet path (`pipeline: "movenet"`) on a machine with
      TensorFlow 2.15 + Python 3.10/3.11

## Pet form and trends (automated)

```bash
pnpm --filter @workspace/silverpaws-beta run test
```

That command covers:

- pet form: a blank name is not valid, so the page does not save
- pet form: age or weight that is present but not a positive number is rejected
- pet form: a blank age and weight, with a name, can be saved
- history trends: an empty list produces no series
- history trends: walks from `movenet` and `opencv-motion` stay in separate series
- history trends: a missing score stays null and is not drawn as zero

The history page still shows the empty-state “Record a walk” link when no
walks are saved (`data-testid="link-history-start-analysis"`). That screen is
not browser-automated here.

## Optional language-model rewrite

`pnpm --filter @workspace/api-server run test` covers three provider cases with
a mock `fetch`:

- no `SILVERPAWS_LLM_*` variables → rule-based text, `usedLlm: false`
- a rewrite that only quotes measured values → that text, `usedLlm: true`
- a rewrite that invents a number → discarded, rule-based text shown, `usedLlm: false`

A live clip with a real provider was not run. No endpoint was configured.

Existing browser test (Chromium on Replit):

```bash
node artifacts/silverpaws-beta/tests/report-download.browser.mjs
```

That test expects `CHROMIUM_PATH` and is not required for a local Windows run.

## What is not tested here

- Live TensorFlow Hub download of MoveNet (this environment has OpenCV only)
- Live LLM provider (the request is unit-tested with a mock; no live endpoint was configured)
- `lib/db` — unused in the beta

## Phase 6 record (October 18, 2026)

Checks that passed in this environment:

- `python -m unittest discover -s tests -t .` — 55 passed
- `pnpm --filter @workspace/api-server run test` — 35 passed
- `pnpm --filter @workspace/silverpaws-beta run test` — 9 passed
- `pnpm run typecheck` — passed
- `npx tsc --noEmit` in `mobile/` — passed
- `npx expo-doctor` in `mobile/` — 21/21 passed
- GitHub checks on pull request 1 — `gh pr checks` reported no checks on this branch. None were failing because none were reported.
- Workspace lint — there is no lint script and no ESLint config. That command was not run, and it is not recorded as passed. Typecheck is the static check this repo has.
- No `SILVERPAWS_LLM_*` variables were set. `POST /api/analyze` of a synthetic clip returned `usedLlm: false`.
- Mock provider, from `artifacts/api-server/tests/explanation.test.ts`: a valid rewrite sets `usedLlm: true`; an invalid rewrite is discarded and the rule-based note stays (`usedLlm: false`).
- Low-confidence keypoints, from `tests/test_model_phase.py`: confidence 0.1 is not trusted, `framesUsed` is 0, and the summary is not treated as missing. A missing score is the words "Not measured" or "Not scored", not zero (`mobile/src/lib/format.ts`, trend tests, report test).
- Non-video upload: `POST /api/analyze` with `notes.txt` returned 400, "That file is not a video SilverPaws can read. MP4, MOV, and WebM work best."
- Oversized upload: the server was started with `MAX_UPLOAD_MB=1` (the default in code is 60). A body over that cap returned 413, "That clip is larger than the 1 MB beta limit. Try a shorter clip."
- OpenCV was attempted. A generated moving rectangle (not a pet, and not a file from the repo) was analyzed with `analyze_clip(..., use_pose=False)` and again through `POST /api/analyze`. Both returned `pipeline: "opencv-motion"`, `aiUse: ["motion-fallback", "scoring", "observation-rules"]`, and null stride symmetry. The same file with pose requested also returned `opencv-motion`, because TensorFlow is not installed.
- The screen lines for that `aiUse` list, from `aiUseResultLines`, are the registry sentences for motion, scoring, and rules. `development` is not included. The phone screen was not opened, so the pixels were not compared.

Checks that were not run, and are not passed:

- UI → API → pipeline with a real walking clip. The repository has no `.mp4`, `.mov`, or `.webm`. No phone or browser was used.
- MoveNet on a real clip. `import tensorflow` fails with `ModuleNotFoundError`. Pose was not measured.
- The low-confidence banner on a phone. The banner code is in the Analyze and walk-detail screens. It was not shown, because MoveNet did not run.
- Server down → the phone's offline note, Retry, and the kept clip. The API process was stopped and `curl` to it failed. The phone UI was not opened. The Analyze screen keeps `clip` on error and shows Try again; that path was not exercised on a device.
- Demo mode on a phone. Unit tests drop the sample from history, trends helpers, and the vet summary. The Demo screen was not opened.
- A live language-model provider. No endpoint was configured.
- `node artifacts/silverpaws-beta/tests/report-download.browser.mjs` — needs `CHROMIUM_PATH`.
- Docker image build. The `docker` command is still not installed.

Copy scan, not a sign-off of the product task: user-facing strings deny diagnosis and point a concerning change to a veterinarian. The emergency note names pain as a reason to call a clinic, not as something the app detects. The product/research card in `TEAM_TASKS.md` stays open. Abhi's live provider walk-through stays open.
