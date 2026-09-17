# SilverPaws AI architecture

## System flow

```text
USER
  ↓
PET PROFILE          artifacts/silverpaws-beta/src/pages/pet.tsx
  ↓
UPLOAD CLIP          pages/analyze.tsx  →  lib/analysis-api.ts
  ↓
VALIDATION           file type / size / duration (UI + API)
  ↓
API                  POST /api/analyze  (multipart video)
  ↓
PYTHON PIPELINE      scripts/analyze_clip.py → gait_engine.pipeline.analyze_clip
  ↓
FRAMES               gait_engine/motion.py
  ↓
POSE (optional)      gait_engine/movenet.py
  ↓
FEATURES             gait_engine/features.py, gait_engine/metrics.py
  ↓
WELLNESS MODEL       gait_engine/wellness.py
  ↓
AI EXPLANATION       api-server/src/lib/explanation.ts
                     (rule-based text in, optional rewrite out)
  ↓
localStorage         src/lib/storage.ts
  ↓
DASHBOARD / HISTORY  pages/home.tsx, pages/history.tsx
```

The UI never runs the vision pipeline. It sends a file and stores the JSON
that comes back.

The mobile app (`mobile/`) follows the same path with different first and last
steps: `app/(tabs)/analyze.tsx → src/lib/api.ts → POST /api/analyze`, and the
result is stored in AsyncStorage by `src/lib/storage.ts`. Both clients share
one API contract, so a walk analyzed from a phone and a walk analyzed from a
browser produce the same record shape.

## Module map

### Frontend — `artifacts/silverpaws-beta/src`

- `App.tsx` — routes
- `pages/pet.tsx` — profile form
- `pages/analyze.tsx` — upload, review, processing, errors
- `pages/home.tsx` — overview
- `pages/history.tsx` — list + detail (measurements vs interpretation)
- `components/trend-panel.tsx` — **Kavin**: trend view (placeholder)
- `lib/storage.ts` — pets and analyses in `localStorage`
- `lib/analysis-api.ts` — upload checks and API error messages
- `lib/report.ts` — browser PDF from a saved record
- `lib/disclaimers.ts` — safety copy used in the footer

### Mobile — `mobile/` (Expo Go, standalone npm project)

- `app/_layout.tsx` — providers and root stack
- `app/(tabs)/` — Home, Analyze (record/choose clip, upload progress), History, Settings
- `app/history/[id].tsx` — one walk: factors, raw measurements, share, delete
- `app/pet/[id].tsx` — pet form (`new` creates); **Kavin**: validation messages
- `src/lib/api.ts` — API address discovery from the Expo dev server, clip checks, XHR upload with progress, error text
- `src/lib/storage.ts` — AsyncStorage version of the web storage module
- `src/lib/types.ts` — hand-mirrored `AnalyzeResult` (source of truth: `lib/api-spec/openapi.yaml`)
- `src/components/trend-panel.tsx` — **Kavin**: trend view (placeholder)
- `metro.config.js` — pins Metro to `mobile/` so it ignores the pnpm workspace above

### API — `artifacts/api-server/src`

- `routes/analyze.ts` — multipart parse, size cap, temp file, JSON reply
- `lib/analysis-runner.ts` — spawn Python, validate against `@workspace/api-zod`
- `lib/explanation.ts` — **Abhi**: provider rewrite; validation is done
- `lib/multipart.ts` — small multipart reader (no extra npm dependency)

### Analysis — `gait_engine/`

- `motion.py` — OpenCV frame motion
- `movenet.py` — pose landmarks
- `metrics.py` — left/right ankle symmetry
- `features.py` — consistency, coverage, hip stability
- `wellness.py` — **Sudarshan**: mobility + historical-change scoring
- `pipeline.py` — chooses `movenet` or `opencv-motion`, builds `AnalyzeResult`

### Contracts — `lib/`

- `lib/api-spec/openapi.yaml` — `/api/analyze` and `/api/healthz`
- `lib/api-zod` / `lib/api-client-react` — generated from that spec
- `lib/db` — Drizzle stub; unused in the beta

## Human vs AI

**Human-developable:** routing, forms, local storage, upload handling, history
layout, PDF assembly, error messages, disclaimers.

**AI / ML:** pose inference, movement features, gait metrics, factor scoring,
observation text, optional LLM rewrite.

## Measurements vs interpretation

A saved analysis keeps both:

- `measurements` — frames, motion mean/std/coverage, symmetry, hip stability
- `factors` / `overallScore` / `observation` — scores and wording

`None` / “Not measured” means the clip did not support that value. It never
means zero.

## Error handling

| Failure | What the user sees |
| --- | --- |
| Missing / non-video file | 400 with a plain message |
| Unreadable / corrupt video | 400 from the pipeline |
| Upload too large | 413 |
| Python missing or crash | 502 |
| Pipeline timeout | 502 |
| API unreachable | UI: “Could not reach the analysis service…” |
| LLM rewrite invalid | Rule-based observation; `usedLlm: false` |

Temporary upload files are deleted after each request.

## Extensibility

- Sudarshan can change scoring without touching the UI
- Kavin can chart saved records without touching the pipeline
- Abhi can add a model provider without changing `gait_engine`
