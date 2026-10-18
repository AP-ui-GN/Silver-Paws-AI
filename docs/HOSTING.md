# Host the analysis API

The phone app sends a walking clip to this API. The API runs the Python
pipeline and deletes the upload. Nothing here is an account system.

This document prepares a container and the steps for one host. It does not
mean a server is already running, and it does not include a public URL.

## What the image contains

`Dockerfile` uses Node 20 and Debian bookworm's Python 3.11. TensorFlow 2.15
does not run on Python 3.12. The image installs `opencv-python-headless` (the
laptop file `requirements.txt` uses `opencv-python`, which expects a display),
NumPy, and TensorFlow at the versions in `requirements-docker.txt`.

While the image builds, `scripts/cache_movenet.py` downloads MoveNet Thunder
into `/app/models/tfhub`. A later request reuses that cache.

The container listens on port 8080. `GET /api/healthz` returns `{ "status": "ok" }`.
That path stays on plain HTTP so the Docker healthcheck can call localhost.
Every other path requires HTTPS when `NODE_ENV=production`. The host's proxy
sets `X-Forwarded-Proto: https`. Local `docker compose` keeps
`NODE_ENV=development`, so `http://127.0.0.1:8080` works on your machine.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8080` | Listen port |
| `NODE_ENV` | unset | `production` turns on the HTTPS check |
| `MAX_UPLOAD_MB` | `60` | Largest clip accepted |
| `ANALYSIS_TIMEOUT_MS` | `120000` | Stop a pipeline run after this many milliseconds |
| `ANALYZE_RATE_LIMIT_PER_MINUTE` | `10` | Analyses allowed per client address each minute |
| `SILVERPAWS_PYTHON` | `/opt/venv/bin/python` in the image | Python that runs the pipeline |
| `SILVERPAWS_REPO_ROOT` | `/app` in the image | Where `gait_engine` and `scripts` live |
| `SILVERPAWS_MOVENET_CACHE` | `/app/models/tfhub` in the image | MoveNet weight cache |
| `SILVERPAWS_LLM_URL` | unset | Optional rewrite endpoint. Leave unset to stay on the rule-based note |
| `SILVERPAWS_LLM_KEY` | unset | Bearer token for that endpoint. Never put this in the phone app |
| `SILVERPAWS_LLM_MODEL` | unset | Model name. Required, with the URL, before a rewrite is attempted |

No API key is required for a clip to be measured.

## Memory

Start the service at **2 GB** of RAM. TensorFlow loads MoveNet on a pose
request, and 2 GB is a starting size, not a measurement from a finished image.

To see what a real clip uses:

1. Run one analysis against the hosted API.
2. On a machine with Docker, run `docker stats` and read the `MEM USAGE` column while that request is in progress.
3. On Render, open the service metrics and read memory for the same request.

If the process is killed for running out of memory, raise the plan above 2 GB and repeat one clip. Do not guess a higher number until you have seen a kill or a peak.

## Local Docker

From the repository root, when Docker is installed:

```bash
docker compose up --build
```

Then open `http://127.0.0.1:8080/api/healthz`.

This environment did not have a `docker` command, so this image was not built here.

## Deploy on Render

Render is the host described here because a Docker web service, a health check, and HTTPS are all in one place. Fly.io or Railway can run the same Dockerfile. None of them has been given this project.

1. Push the repository to GitHub.
2. In Render, create a **Web Service** and choose **Docker**. Set the root to the repository root so `Dockerfile` is used.
3. Set the health check path to `/api/healthz`.
4. Choose an instance with at least 2 GB of RAM.
5. Set `NODE_ENV` to `production` and set any other variables from the table. Leave the language-model variables empty unless you have a provider.
6. Deploy. Render serves HTTPS. The first pose request should not download MoveNet, because the image build already cached it.
7. Copy the `https://` address Render shows. That address is `EXPO_PUBLIC_API_URL` for the phone build. Do not invent one in the repo.

The phone build does not contain `SILVERPAWS_LLM_KEY` or any other server secret. `EXPO_PUBLIC_API_URL` is public by design. It is only the API address.
