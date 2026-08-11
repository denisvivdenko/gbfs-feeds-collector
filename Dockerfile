FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY data/ data/
RUN uv sync --frozen --no-dev

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}"

# Storage backend to write raw GBFS payloads to: "fs" (local filesystem) or "s3".
ENV STORAGE=fs
# Per-feed crawl intervals are configured in data/feeds_schedule.yaml.
# Maximum number of providers to crawl per run (unset = no limit).
# ENV LIMIT_PROVIDERS_CRAWLED=10

ENTRYPOINT ["/app/entrypoint.sh"]
