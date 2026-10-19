# Analysis API plus the Python gait pipeline.
# Node 20. Python 3.11 from Debian bookworm (TensorFlow 2.15 does not run on 3.12).
# MoveNet weights are downloaded while the image builds, not on the first request.

FROM node:20-bookworm-slim AS build

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates python3 \
  && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare pnpm@10.33.4 --activate

WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY artifacts ./artifacts
COPY lib ./lib
COPY scripts ./scripts
COPY gait_engine ./gait_engine

RUN pnpm install --frozen-lockfile --filter @workspace/api-server...
RUN pnpm --filter @workspace/api-server run build

FROM node:20-bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    python3-venv \
    python3-pip \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=build /app/artifacts/api-server/dist ./artifacts/api-server/dist
COPY gait_engine ./gait_engine
COPY scripts/analyze_clip.py scripts/cache_movenet.py ./scripts/
COPY requirements-docker.txt ./

RUN python3 -m venv /opt/venv \
  && /opt/venv/bin/pip install --no-cache-dir -r requirements-docker.txt \
  && SILVERPAWS_MOVENET_CACHE=/app/models/tfhub /opt/venv/bin/python scripts/cache_movenet.py

ENV NODE_ENV=production \
    PORT=8080 \
    SILVERPAWS_PYTHON=/opt/venv/bin/python \
    SILVERPAWS_REPO_ROOT=/app \
    SILVERPAWS_MOVENET_CACHE=/app/models/tfhub \
    MAX_UPLOAD_MB=60 \
    ANALYSIS_TIMEOUT_MS=120000 \
    ANALYZE_RATE_LIMIT_PER_MINUTE=10

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||8080)+'/api/healthz').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "--enable-source-maps", "artifacts/api-server/dist/index.mjs"]
