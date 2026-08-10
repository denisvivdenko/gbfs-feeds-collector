from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from gbfs_feeds_collector.crawlers.crawler_exceptions import (
    DownloadError,
    JSONFormatError,
    MissingLastUpdatedError,
)
from gbfs_feeds_collector.crawlers.gbfs_entity_crawler import (
    LAST_UPDATED_FORMAT,
    fetch_gbfs_entity,
)
from gbfs_feeds_collector.parsers import Provider, parse_feeds, parse_providers
from gbfs_feeds_collector.settings import settings
from gbfs_feeds_collector.storage import LocalFileSystemStorage, ObjectStorage, S3Storage

logger = logging.getLogger(__name__)

_FETCH_ERRORS = (DownloadError, JSONFormatError, MissingLastUpdatedError)


def collect_data_from_gbfs_feeds(
    providers: list[Provider], storage: ObjectStorage, limit: int | None = None
) -> None:
    for provider in providers[:limit]:
        try:
            _, discovery_payload = fetch_gbfs_entity(str(provider.url))
            feeds = parse_feeds(discovery_payload)
        except _FETCH_ERRORS as error:
            logger.warning("Skipping provider %s: %s", provider.id, error)
            continue

        for feed in feeds:
            try:
                last_updated, payload = fetch_gbfs_entity(str(feed.url))
            except _FETCH_ERRORS as error:
                logger.warning(
                    "Skipping feed %s for provider %s: %s", feed.name, provider.id, error
                )
                continue

            key = f"{provider.id}/{feed.name}/{last_updated.strftime(LAST_UPDATED_FORMAT)}.json"
            storage.save(key, json.dumps(payload).encode("utf-8"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl GBFS feeds for providers and save the raw JSON responses."
    )
    parser.add_argument(
        "--providers-csv-path",
        type=Path,
        default=settings.gbfs_providers_csv_path,
        help=f"Path to the providers CSV to read (default: {settings.gbfs_providers_csv_path}).",
    )
    parser.add_argument(
        "--storage",
        choices=["local", "s3"],
        default="local",
        help="Object storage backend to save raw GBFS feed JSON files to (default: local).",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=settings.gbfs_feeds_dir,
        help="Root directory to save raw GBFS feed JSON files to when using local storage "
        f"(default: {settings.gbfs_feeds_dir}).",
    )
    parser.add_argument(
        "--s3-bucket",
        default=None,
        help="S3 bucket to save raw GBFS feed JSON files to when using s3 storage.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of providers to crawl (default: no limit).",
    )
    args = parser.parse_args()
    if args.storage == "s3" and not args.s3_bucket:
        parser.error("--s3-bucket is required when --storage=s3")
    return args


def _build_storage(args: argparse.Namespace) -> ObjectStorage:
    if args.storage == "s3":
        return S3Storage(args.s3_bucket)
    return LocalFileSystemStorage(args.output_path)


def main() -> None:
    args = _parse_args()
    providers = parse_providers(args.providers_csv_path.read_bytes())
    storage = _build_storage(args)
    collect_data_from_gbfs_feeds(providers, storage, limit=args.limit)


if __name__ == "__main__":
    main()
