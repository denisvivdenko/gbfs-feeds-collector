import asyncio

import httpx

from gbfs_feeds_collector.parsers import Provider
from gbfs_feeds_collector.pipelines.collect_data_from_gbfs_feeds import (
    collect_data_from_gbfs_feeds,
)
from gbfs_feeds_collector.storage import LocalFileSystemStorage

LAST_UPDATED = "2026-08-10T11:38:42Z"


def _gbfs_payload(data: dict) -> dict:
    return {"last_updated": LAST_UPDATED, "ttl": 30, "version": "3.0", "data": data}


def _provider(provider_id: str, discovery_url: str) -> Provider:
    return Provider(
        id=provider_id, name=provider_id, url=discovery_url, supported_versions=["3.0"]
    )


def _patch_async_client(monkeypatch, handler) -> None:
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real_async_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", factory)


async def test_collect_data_from_gbfs_feeds_skips_feed_names_not_in_schedule(
    tmp_path, monkeypatch
):
    provider = _provider("p1", "https://example.com/p1/gbfs.json")
    schedule = {"station_status": 60}
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))
        if str(request.url) == "https://example.com/p1/gbfs.json":
            return httpx.Response(
                200,
                json=_gbfs_payload(
                    {
                        "feeds": [
                            {
                                "name": "station_status",
                                "url": "https://example.com/p1/station_status.json",
                            },
                            {
                                "name": "system_alerts",
                                "url": "https://example.com/p1/system_alerts.json",
                            },
                        ]
                    }
                ),
            )
        if str(request.url) == "https://example.com/p1/station_status.json":
            return httpx.Response(200, json=_gbfs_payload({"stations": []}))
        raise AssertionError(f"unexpected request to {request.url}")

    _patch_async_client(monkeypatch, handler)
    storage = LocalFileSystemStorage(tmp_path)

    stats = await collect_data_from_gbfs_feeds([provider], storage, schedule, max_cycles=1)

    assert "https://example.com/p1/system_alerts.json" not in requested_urls
    assert storage.list_keys("p1") == [f"p1/station_status/{LAST_UPDATED}.json"]
    assert stats.feeds_processed == 1


async def test_collect_data_from_gbfs_feeds_crawls_a_feed_name_across_all_providers_that_expose_it(
    tmp_path, monkeypatch
):
    providers = [
        _provider("p1", "https://example.com/p1/gbfs.json"),
        _provider("p2", "https://example.com/p2/gbfs.json"),
    ]
    schedule = {"station_status": 60}

    def handler(request):
        url = str(request.url)
        if url == "https://example.com/p1/gbfs.json":
            return httpx.Response(
                200,
                json=_gbfs_payload(
                    {
                        "feeds": [
                            {
                                "name": "station_status",
                                "url": "https://example.com/p1/station_status.json",
                            }
                        ]
                    }
                ),
            )
        if url == "https://example.com/p2/gbfs.json":
            return httpx.Response(
                200,
                json=_gbfs_payload(
                    {
                        "feeds": [
                            {
                                "name": "station_status",
                                "url": "https://example.com/p2/station_status.json",
                            }
                        ]
                    }
                ),
            )
        if url in (
            "https://example.com/p1/station_status.json",
            "https://example.com/p2/station_status.json",
        ):
            return httpx.Response(200, json=_gbfs_payload({"stations": []}))
        raise AssertionError(f"unexpected request to {url}")

    _patch_async_client(monkeypatch, handler)
    storage = LocalFileSystemStorage(tmp_path)

    stats = await collect_data_from_gbfs_feeds(providers, storage, schedule, max_cycles=1)

    assert storage.list_keys("p1") == [f"p1/station_status/{LAST_UPDATED}.json"]
    assert storage.list_keys("p2") == [f"p2/station_status/{LAST_UPDATED}.json"]
    assert stats.feeds_processed == 2


async def test_collect_data_from_gbfs_feeds_repeats_per_feed_schedule_for_max_cycles(
    tmp_path, monkeypatch
):
    provider = _provider("p1", "https://example.com/p1/gbfs.json")
    schedule = {"station_status": 60}
    feed_calls = []

    def handler(request):
        url = str(request.url)
        if url == "https://example.com/p1/gbfs.json":
            return httpx.Response(
                200,
                json=_gbfs_payload(
                    {
                        "feeds": [
                            {
                                "name": "station_status",
                                "url": "https://example.com/p1/station_status.json",
                            }
                        ]
                    }
                ),
            )
        if url == "https://example.com/p1/station_status.json":
            feed_calls.append(url)
            return httpx.Response(200, json=_gbfs_payload({"stations": []}))
        raise AssertionError(f"unexpected request to {url}")

    _patch_async_client(monkeypatch, handler)

    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    storage = LocalFileSystemStorage(tmp_path)

    stats = await collect_data_from_gbfs_feeds([provider], storage, schedule, max_cycles=2)

    assert len(feed_calls) == 2
    assert stats.feeds_processed == 2
    assert sleep_calls == [60]


async def test_collect_data_from_gbfs_feeds_continues_after_a_provider_discovery_failure(
    tmp_path, monkeypatch
):
    healthy = _provider("p1", "https://example.com/p1/gbfs.json")
    broken = _provider("p2", "https://example.com/p2/gbfs.json")
    schedule = {"station_status": 60}

    def handler(request):
        url = str(request.url)
        if url == "https://example.com/p1/gbfs.json":
            return httpx.Response(
                200,
                json=_gbfs_payload(
                    {
                        "feeds": [
                            {
                                "name": "station_status",
                                "url": "https://example.com/p1/station_status.json",
                            }
                        ]
                    }
                ),
            )
        if url == "https://example.com/p2/gbfs.json":
            return httpx.Response(500, text="internal error")
        if url == "https://example.com/p1/station_status.json":
            return httpx.Response(200, json=_gbfs_payload({"stations": []}))
        raise AssertionError(f"unexpected request to {url}")

    _patch_async_client(monkeypatch, handler)
    storage = LocalFileSystemStorage(tmp_path)

    stats = await collect_data_from_gbfs_feeds(
        [healthy, broken], storage, schedule, max_cycles=1
    )

    assert stats.providers_failed == 1
    assert stats.providers_processed == 1
    assert storage.list_keys("p1") == [f"p1/station_status/{LAST_UPDATED}.json"]
    assert storage.list_keys("p2") == []
