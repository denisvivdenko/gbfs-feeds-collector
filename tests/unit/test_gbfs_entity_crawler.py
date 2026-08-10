from datetime import datetime, timezone

import httpx
import pytest

from gbfs_feeds_collector.crawlers.crawler_exceptions import (
    DownloadError,
    JSONFormatError,
    MissingLastUpdatedError,
)
from gbfs_feeds_collector.crawlers.gbfs_entity_crawler import fetch_gbfs_entity


@pytest.fixture
def url():
    return "https://example.com/gbfs.json"


@pytest.fixture
def gbfs_payload():
    return {
        "last_updated": "2026-08-10T11:38:42Z",
        "ttl": 30,
        "version": "3.0",
        "data": {"feeds": []},
    }


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_fetch_gbfs_entity_returns_parsed_date_and_payload(url, gbfs_payload):
    def handler(request):
        return httpx.Response(200, json=gbfs_payload)

    async with _client(handler) as client:
        last_updated, payload = await fetch_gbfs_entity(client, url)

    assert last_updated == datetime(2026, 8, 10, 11, 38, 42, tzinfo=timezone.utc)
    assert payload == gbfs_payload


async def test_fetch_gbfs_entity_raises_download_error_when_download_fails(url):
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    async with _client(handler) as client:
        with pytest.raises(DownloadError) as exc_info:
            await fetch_gbfs_entity(client, url)

    assert url in str(exc_info.value)


async def test_fetch_gbfs_entity_raises_download_error_when_response_is_an_http_error(url):
    def handler(request):
        return httpx.Response(500, text="internal error")

    async with _client(handler) as client:
        with pytest.raises(DownloadError) as exc_info:
            await fetch_gbfs_entity(client, url)

    assert url in str(exc_info.value)


async def test_fetch_gbfs_entity_raises_json_format_error_when_body_is_not_valid_json(url):
    def handler(request):
        return httpx.Response(200, text="not-valid-json")

    async with _client(handler) as client:
        with pytest.raises(JSONFormatError) as exc_info:
            await fetch_gbfs_entity(client, url)

    assert url in str(exc_info.value)


async def test_fetch_gbfs_entity_raises_date_error_when_last_updated_is_missing(
    url, gbfs_payload
):
    del gbfs_payload["last_updated"]

    def handler(request):
        return httpx.Response(200, json=gbfs_payload)

    async with _client(handler) as client:
        with pytest.raises(MissingLastUpdatedError) as exc_info:
            await fetch_gbfs_entity(client, url)

    assert url in str(exc_info.value)


async def test_fetch_gbfs_entity_raises_date_error_when_last_updated_has_wrong_format(
    url, gbfs_payload
):
    gbfs_payload["last_updated"] = "2026-08-10"

    def handler(request):
        return httpx.Response(200, json=gbfs_payload)

    async with _client(handler) as client:
        with pytest.raises(MissingLastUpdatedError) as exc_info:
            await fetch_gbfs_entity(client, url)

    assert "2026-08-10" in str(exc_info.value)
