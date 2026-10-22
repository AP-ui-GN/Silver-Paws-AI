# Validation runbook

This document separates checks that can run in CI from checks that require real,
licensed dog footage or credentials supplied by a project maintainer.

## 1. Dog-pose accuracy: labeled real-dog clips

Do not use generated/synthetic motion clips as evidence of dog-keypoint accuracy.
The container smoke test checks that the image builds, the API becomes ready, and
the analysis endpoint responds; it is not an accuracy benchmark.

### Dataset intake checklist

Before adding a clip to a local validation set, record:

- exact source URL or source identifier;
- license name and URL, including permission for downloading, processing, and
  derived annotations;
- whether the dog owner/filmer consented to this use, where applicable;
- clip filename, camera view, approximate walking direction, and quality notes;
- independent label and labeler/reviewer; resolve disagreements before scoring.

Only use footage whose license and consent terms permit this project’s intended
use. Do not assume that a publicly viewable video is licensed for reuse. Do not
commit clips, frames, personal information, or credentials to Git. Keep clips in
the gitignored `validation_clips/` directory and keep a provenance record in
`validation_clips/labels.csv` with columns:
`file,label,source,license,notes`. The current coarse label values are
`normal`, `mild`, and `significant`; these are screening labels, not
veterinary diagnoses.

### Run and review

1. Confirm that every listed file exists and that the provenance/license fields
   are complete.
2. Run the validation command from the repository root:

   ```bash
   python scripts/validate_gait.py --clips-dir validation_clips \
     --labels validation_clips/labels.csv --out outputs/validation.csv
   ```

3. Inspect per-clip output and failure cases; do not rely on aggregate scores
   alone. Record the commit SHA, environment, dataset version, and command.
4. Keep a fixed held-out set for final comparisons. Do not tune thresholds on
   the held-out clips.
5. Report sample size, class balance, camera angles, exclusions, and uncertainty.
   A small convenience sample is exploratory only and must not be described as
   clinical validation.

A missing clip directory or labels file must be treated as an incomplete run,
not a passing validation. The command exits nonzero for missing prerequisites.

## 2. Optional language-model rewrite: live provider smoke test

Unit tests use a mock provider. A live provider test requires a project
maintainer to supply a reachable, compatible endpoint and credentials if the
provider requires them. Do not add secrets to source files, pull requests,
screenshots, or logs.

The application’s documented configuration includes
`SILVERPAWS_LLM_URL` and `SILVERPAWS_LLM_MODEL`. Confirm the provider's API
contract and authentication requirements before testing; do not assume every
OpenAI-compatible endpoint is interchangeable.

1. Configure the variables only in a local untracked environment file or the
   hosting provider's secret manager. Use a least-privilege test key.
2. Start the API and submit a short, consented test clip through the normal
   `POST /api/analyze` flow.
3. Confirm that a valid rewrite is marked `usedLlm: true` and only restates
   values in the measured observation.
4. Test a deliberately invalid/invented-number response in a controlled mock
   test and confirm that the rewrite is discarded and the rule-based note is
   returned. Never depend on a live model to reliably produce a malicious or
   invalid response on demand.
5. Verify that provider errors/timeouts fall back to the rule-based note, and
   that logs do not expose API keys or sensitive clip data.
6. Record provider/model identifier, date, commit SHA, pass/fail, and redacted
   error details. Never record the key itself.

If no real endpoint and credentials are available, report the live-provider
check as **not run**. Passing mocked tests does not count as a live provider test.

## 3. Evidence matrix

| Check | What it establishes | What it does not establish |
| --- | --- | --- |
| Unit/synthetic tests | Code paths and known edge cases | Accuracy on real dogs |
| Docker/API smoke test | Packaging, readiness, basic endpoint integration | Pose accuracy or production capacity |
| Labeled dog clips | Preliminary agreement with the chosen labels | Veterinary diagnosis or broad generalization by itself |
| Live provider test | One configured provider flow at test time | Provider reliability for all future requests |

Never describe SilverPaws as diagnosing a condition. Keep the product language
focused on observable movement changes and encourage veterinary assessment when
an owner is concerned.
