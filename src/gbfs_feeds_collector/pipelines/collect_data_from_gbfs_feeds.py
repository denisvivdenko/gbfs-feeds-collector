from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import httpx

from gbfs_feeds_collector.crawlers.crawler_exceptions import (
    DownloadError,
    JSONFormatError,
    MissingLastUpdatedError,
)
from gbfs_feeds_collector.crawlers.gbfs_entity_crawler import (
    LAST_UPDATED_FORMAT,
    fetch_gbfs_entity,
)
from gbfs_feeds_collector.feed_schedule import FeedSchedule, load_feed_schedule
from gbfs_feeds_collector.logging_config import configure_logging
from gbfs_feeds_collector.parsers import (
    Feed,
    Provider,
    is_gbfs_v3_provider,
    parse_feeds,
    parse_providers,
)
from gbfs_feeds_collector.settings import settings
from gbfs_feeds_collector.storage import LocalFileSystemStorage, ObjectStorage, S3Storage

logger = logging.getLogger(__name__)

_FETCH_ERRORS = (DownloadError, JSONFormatError, MissingLastUpdatedError)

DEFAULT_CONCURRENCY = 20


@dataclass
class CrawlStats:
    providers_total: int = 0
    providers_processed: int = 0
    providers_failed: int = 0
    feeds_processed: int = 0
    feeds_failed: int = 0

    @property
    def errors(self) -> int:
        return self.providers_failed + self.feeds_failed


async def _crawl_feed(
    client: httpx.AsyncClient,
    storage: ObjectStorage,
    semaphore: asyncio.Semaphore,
    provider: Provider,
    feed: Feed,
    stats: CrawlStats,
) -> None:
    async with semaphore:
        try:
            last_updated, payload = await fetch_gbfs_entity(client, str(feed.url))
        except _FETCH_ERRORS as error:
            stats.feeds_failed += 1
            logger.warning(
                "Skipping feed %s for provider %s: %s",
                feed.name,
                provider.id,
                error,
                extra={
                    "provider_id": provider.id,
                    "feed_name": feed.name,
                    "error": str(error),
                },
            )
            return

    key = f"{provider.id}/{feed.name}/{last_updated.strftime(LAST_UPDATED_FORMAT)}.json"
    await asyncio.to_thread(storage.save, key, json.dumps(payload).encode("utf-8"))
    stats.feeds_processed += 1
    logger.debug(
        "Saved feed %s for provider %s to %s",
        feed.name,
        provider.id,
        key,
        extra={
            "provider_id": provider.id,
            "feed_name": feed.name,
            "storage_key": key,
        },
    )


async def _discover_feeds(
    client: httpx.AsyncClient,
    providers: list[Provider],
    schedule: FeedSchedule,
    semaphore: asyncio.Semaphore,
    stats: CrawlStats,
) -> dict[str, list[tuple[Provider, Feed]]]:
    feeds_by_name: dict[str, list[tuple[Provider, Feed]]] = defaultdict(list)

    async def discover_one(provider: Provider) -> None:
        async with semaphore:
            try:
                _, discovery_payload = await fetch_gbfs_entity(client, str(provider.url))
                feeds = parse_feeds(discovery_payload)
            except _FETCH_ERRORS as error:
                stats.providers_failed += 1
                logger.warning(
                    "Skipping provider %s: %s",
                    provider.id,
                    error,
                    extra={"provider_id": provider.id, "error": str(error)},
                )
                return

        stats.providers_processed += 1
        scheduled_feeds = [feed for feed in feeds if feed.name in schedule]
        logger.debug(
            "Discovered %d feed(s) for provider %s, %d scheduled",
            len(feeds),
            provider.id,
            len(scheduled_feeds),
            extra={
                "provider_id": provider.id,
                "feeds_discovered": len(feeds),
                "feeds_scheduled": len(scheduled_feeds),
            },
        )
        for feed in scheduled_feeds:
            feeds_by_name[feed.name].append((provider, feed))

    await asyncio.gather(*(discover_one(provider) for provider in providers))
    return feeds_by_name


async def _run_feed_schedule(
    feed_name: str,
    entries: list[tuple[Provider, Feed]],
    interval_seconds: int,
    client: httpx.AsyncClient,
    storage: ObjectStorage,
    semaphore: asyncio.Semaphore,
    stats: CrawlStats,
    max_cycles: int | None,
) -> None:
    cycle = 0
    while True:
        await asyncio.gather(
            *(
                _crawl_feed(client, storage, semaphore, provider, feed, stats)
                for provider, feed in entries
            )
        )
        cycle += 1
        logger.info(
            "Completed crawl cycle %d for feed %s (%d source(s))",
            cycle,
            feed_name,
            len(entries),
            extra={"feed_name": feed_name, "cycle": cycle, "sources": len(entries)},
        )
        if max_cycles is not None and cycle >= max_cycles:
            return
        await asyncio.sleep(interval_seconds)


async def collect_data_from_gbfs_feeds(
    providers: list[Provider],
    storage: ObjectStorage,
    schedule: FeedSchedule,
    limit: int | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    max_cycles: int | None = None,
) -> CrawlStats:
    providers = providers[:limit]
    logger.info("Starting crawl of %d provider(s)", len(providers))

    stats = CrawlStats(providers_total=len(providers))
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        feeds_by_name = await _discover_feeds(client, providers, schedule, semaphore, stats)

        missing = set(schedule) - set(feeds_by_name)
        if missing:
            logger.info(
                "No provider currently exposes feed(s): %s",
                ", ".join(sorted(missing)),
                extra={"missing_feeds": sorted(missing)},
            )

        await asyncio.gather(
            *(
                _run_feed_schedule(
                    feed_name,
                    entries,
                    schedule[feed_name],
                    client,
                    storage,
                    semaphore,
                    stats,
                    max_cycles,
                )
                for feed_name, entries in feeds_by_name.items()
            )
        )

    logger.info(
        "Finished crawl",
        extra={
            "providers_total": stats.providers_total,
            "providers_processed": stats.providers_processed,
            "providers_failed": stats.providers_failed,
            "feeds_processed": stats.feeds_processed,
            "feeds_failed": stats.feeds_failed,
            "errors": stats.errors,
        },
    )
    return stats


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
        "--feeds-schedule-path",
        type=Path,
        default=settings.gbfs_feeds_schedule_path,
        help="Path to the YAML file mapping feed name to crawl interval in seconds. "
        f"Feed names not listed are skipped entirely (default: {settings.gbfs_feeds_schedule_path}).",
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
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Maximum number of concurrent HTTP requests in flight "
        f"(default: {DEFAULT_CONCURRENCY}).",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Number of crawl cycles to run per feed before exiting (default: run forever).",
    )
    args = parser.parse_args()
    if args.storage == "s3" and not args.s3_bucket:
        parser.error("--s3-bucket is required when --storage=s3")
    return args


def _build_storage(args: argparse.Namespace) -> ObjectStorage:
    if args.storage == "s3":
        return S3Storage(args.s3_bucket)
    return LocalFileSystemStorage(args.output_path)


async def _run(args: argparse.Namespace) -> None:
    providers = parse_providers(args.providers_csv_path.read_bytes())
    logger.info("Loaded %d provider(s) from %s", len(providers), args.providers_csv_path)
    providers = [provider for provider in providers if is_gbfs_v3_provider(provider)]
    logger.info("%d provider(s) support GBFS v3", len(providers))
    schedule = load_feed_schedule(args.feeds_schedule_path)
    storage = _build_storage(args)
    await collect_data_from_gbfs_feeds(
        providers,
        storage,
        schedule,
        limit=args.limit,
        concurrency=args.concurrency,
        max_cycles=args.max_cycles,
    )


def main() -> None:
    configure_logging()
    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
