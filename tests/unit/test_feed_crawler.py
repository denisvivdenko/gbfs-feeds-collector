import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pytest

from gbfs_feeds_collector.feed_crawler import (
    Feed,
    FeedDateError,
    FeedDownloadError,
    FeedResponseError,
    fetch_feed,
)


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
def feed():
    return Feed(name="gbfs_versions", url="https://example.com/gbfs.json")


@pytest.fixture
def gbfs_payload():
    return {
        "last_updated": "2026-08-10T11:38:42Z",
        "ttl": 30,
        "version": "3.0",
        "data": {"feeds": []},
    }


def test_fetch_provider_gbfs_returns_parsed_date_and_payload(
    monkeypatch, feed, gbfs_payload
):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda url: _FakeResponse(json.dumps(gbfs_payload).encode("utf-8")),
    )

    last_updated, payload = fetch_feed(feed)

    assert last_updated == datetime(2026, 8, 10, 11, 38, 42, tzinfo=timezone.utc)
    assert payload == gbfs_payload


def test_fetch_provider_gbfs_raises_feed_download_error_when_download_fails(
    monkeypatch, feed
):
    def raise_url_error(url):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", raise_url_error)

    with pytest.raises(FeedDownloadError) as exc_info:
        fetch_feed(feed)

    assert feed.name in str(exc_info.value)
    assert str(feed.url) in str(exc_info.value)


def test_fetch_provider_gbfs_raises_feed_response_error_when_body_is_not_valid_json(
    monkeypatch, feed
):
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda url: _FakeResponse(b"not-valid-json")
    )

    with pytest.raises(FeedResponseError) as exc_info:
        fetch_feed(feed)

    assert feed.name in str(exc_info.value)


def test_fetch_provider_gbfs_raises_feed_date_error_when_last_updated_is_missing(
    monkeypatch, feed, gbfs_payload
):
    del gbfs_payload["last_updated"]
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda url: _FakeResponse(json.dumps(gbfs_payload).encode("utf-8")),
    )

    with pytest.raises(FeedDateError) as exc_info:
        fetch_feed(feed)

    assert feed.name in str(exc_info.value)


def test_fetch_provider_gbfs_raises_feed_date_error_when_last_updated_has_wrong_format(
    monkeypatch, feed, gbfs_payload
):
    gbfs_payload["last_updated"] = "2026-08-10"
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda url: _FakeResponse(json.dumps(gbfs_payload).encode("utf-8")),
    )

    with pytest.raises(FeedDateError) as exc_info:
        fetch_feed(feed)

    assert "2026-08-10" in str(exc_info.value)
