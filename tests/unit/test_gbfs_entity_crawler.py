import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pytest

from gbfs_feeds_collector.crawlers.crawler_exceptions import (
    DateError,
    DownloadError,
    JSONFormatError,
)
from gbfs_feeds_collector.crawlers.gbfs_entity_crawler import fetch_gbfs_entity


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self):
        return self._body


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


def test_fetch_gbfs_entity_returns_parsed_date_and_payload(monkeypatch, url, gbfs_payload):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request_url: _FakeResponse(json.dumps(gbfs_payload).encode("utf-8")),
    )

    last_updated, payload = fetch_gbfs_entity(url)

    assert last_updated == datetime(2026, 8, 10, 11, 38, 42, tzinfo=timezone.utc)
    assert payload == gbfs_payload


def test_fetch_gbfs_entity_raises_download_error_when_download_fails(monkeypatch, url):
    def raise_url_error(request_url):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", raise_url_error)

    with pytest.raises(DownloadError) as exc_info:
        fetch_gbfs_entity(url)

    assert url in str(exc_info.value)


def test_fetch_gbfs_entity_raises_json_format_error_when_body_is_not_valid_json(
    monkeypatch, url
):
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request_url: _FakeResponse(b"not-valid-json")
    )

    with pytest.raises(JSONFormatError) as exc_info:
        fetch_gbfs_entity(url)

    assert url in str(exc_info.value)


def test_fetch_gbfs_entity_raises_date_error_when_last_updated_is_missing(
    monkeypatch, url, gbfs_payload
):
    del gbfs_payload["last_updated"]
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request_url: _FakeResponse(json.dumps(gbfs_payload).encode("utf-8")),
    )

    with pytest.raises(DateError) as exc_info:
        fetch_gbfs_entity(url)

    assert url in str(exc_info.value)


def test_fetch_gbfs_entity_raises_date_error_when_last_updated_has_wrong_format(
    monkeypatch, url, gbfs_payload
):
    gbfs_payload["last_updated"] = "2026-08-10"
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request_url: _FakeResponse(json.dumps(gbfs_payload).encode("utf-8")),
    )

    with pytest.raises(DateError) as exc_info:
        fetch_gbfs_entity(url)

    assert "2026-08-10" in str(exc_info.value)
