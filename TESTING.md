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
- Multipart parsing and explanation validation (18 Node tests)
- Motion statistics, consistency, hip stability, symmetry, scoring, and
  observation text (32 Python tests)

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

## Manual checklist (for teammates)

- [ ] Create and edit a second pet
- [ ] Reject a huge file in the UI before upload
- [ ] Run two clips for the same pet and confirm the second observation
      mentions the score difference
- [ ] Delete an observation and visit its old URL
- [ ] Stop the API and confirm the analyze page shows a reachable-service error
- [ ] Confirm MoveNet path (`pipeline: "movenet"`) on a machine with
      TensorFlow 2.15 + Python 3.10/3.11

## Kavin — selected automated tests

Add at least one of:

- pet form: blank name does not save
- analyze page: non-video file shows `text-upload-error`
- history: empty state link to `/analyze`

Existing browser test (Chromium on Replit):

```bash
node artifacts/silverpaws-beta/tests/report-download.browser.mjs
```

That test expects `CHROMIUM_PATH` and is not required for a local Windows run.

## What is not tested here

- Live TensorFlow Hub download of MoveNet (this environment has OpenCV only)
- Live LLM provider (Abhi’s task; validation is unit-tested without a network)
- `lib/db` — unused in the beta
