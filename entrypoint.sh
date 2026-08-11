#!/usr/bin/env sh
set -eu

STORAGE="${STORAGE:-fs}"

case "$STORAGE" in
  fs|local)
    STORAGE_ARG="local"
    ;;
  s3)
    STORAGE_ARG="s3"
    if [ -z "${S3_BUCKET:-}" ]; then
      echo "S3_BUCKET must be set when STORAGE=s3" >&2
      exit 1
    fi
    ;;
  *)
    echo "Unknown STORAGE '${STORAGE}' (expected 'fs' or 's3')" >&2
    exit 1
    ;;
esac

set -- --storage "$STORAGE_ARG" "$@"
if [ "$STORAGE_ARG" = "s3" ]; then
  set -- "$@" --s3-bucket "$S3_BUCKET"
fi
if [ -n "${LIMIT_PROVIDERS_CRAWLED:-}" ]; then
  set -- "$@" --limit "$LIMIT_PROVIDERS_CRAWLED"
fi

echo "Starting GBFS feed collector (storage=${STORAGE_ARG}, per-feed schedule from data/feeds_schedule.yaml)"

exec python -m gbfs_feeds_collector.pipelines.collect_data_from_gbfs_feeds "$@"
