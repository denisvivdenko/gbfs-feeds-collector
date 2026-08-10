import pytest

from gbfs_feeds_collector.crawlers.feed_crawler import Feed
from gbfs_feeds_collector.parsers.gbfs_parser import parse_feeds


@pytest.fixture
def gbfs_payload():
    return {
        "last_updated": "2026-08-10T11:38:42Z",
        "ttl": 30,
        "version": "3.0",
        "data": {
            "feeds": [
                {"name": "system_information", "url": "https://example.com/system_information.json"},
                {"name": "station_information", "url": "https://example.com/station_information.json"},
            ]
        },
    }


def test_parse_feeds_returns_feed_objects_for_valid_payload(gbfs_payload):
    feeds = parse_feeds(gbfs_payload)

    assert feeds == [
        Feed(name="system_information", url="https://example.com/system_information.json"),
        Feed(name="station_information", url="https://example.com/station_information.json"),
    ]


def test_parse_feeds_returns_empty_list_when_feeds_array_is_empty(gbfs_payload):
    gbfs_payload["data"]["feeds"] = []

    feeds = parse_feeds(gbfs_payload)

    assert feeds == []
