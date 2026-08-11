"""Benchmarks the crawl pipeline against real GBFS provider endpoints.

Excluded from the default test run (see `addopts` in pyproject.toml) since it
makes hundreds of real network calls and is meant to be run deliberately:

    uv run pytest tests/stress -m stress -s
"""

import time

import pytest

from gbfs_feeds_collector.feed_schedule import load_feed_schedule
from gbfs_feeds_collector.parsers import is_gbfs_v3_provider, parse_providers
from gbfs_feeds_collector.pipelines.collect_data_from_gbfs_feeds import (
    collect_data_from_gbfs_feeds,
)
from gbfs_feeds_collector.settings import settings
from gbfs_feeds_collector.storage import LocalFileSystemStorage

SAMPLE_SIZE = 20 


def _sample_providers(limit: int = SAMPLE_SIZE):
    providers = parse_providers(settings.gbfs_providers_csv_path.read_bytes())
    v3_providers = [provider for provider in providers if is_gbfs_v3_provider(provider)]
    return v3_providers[:limit]


def _report(label: str, elapsed: float, providers_total: int, feeds_processed: int) -> None:
    throughput = feeds_processed / elapsed if elapsed else 0.0
    print(
        f"\n[{label}] providers={providers_total} feeds_processed={feeds_processed} "
        f"elapsed={elapsed:.2f}s throughput={throughput:.2f} feeds/s"
    )


@pytest.mark.stress
async def test_concurrent_asyncio_crawl_performance(tmp_path):
    providers = _sample_providers()
    storage = LocalFileSystemStorage(tmp_path)
    schedule = load_feed_schedule(settings.gbfs_feeds_schedule_path)

    start = time.perf_counter()
    stats = await collect_data_from_gbfs_feeds(providers, storage, schedule, max_cycles=1)
    elapsed = time.perf_counter() - start

    _report("concurrent asyncio", elapsed, stats.providers_total, stats.feeds_processed)

    assert stats.feeds_processed > 0
