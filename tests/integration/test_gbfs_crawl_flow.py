import csv

from gbfs_feeds_collector.crawlers.feed_crawler import fetch_feed
from gbfs_feeds_collector.crawlers.gbfs_crawler import fetch_gbfs
from gbfs_feeds_collector.parsers.gbfs_parser import parse_feeds
from gbfs_feeds_collector.crawlers.gbfs_providers_crawler import OUTPUT_PATH


def _first_provider_with_auto_discovery_url():
    with OUTPUT_PATH.open(newline="", encoding="utf-8") as providers_file:
        for row in csv.DictReader(providers_file):
            if row["Auto-Discovery URL"]:
                return row
    raise AssertionError("No provider with an Auto-Discovery URL found")


def test_crawl_gbfs_parse_feeds_and_fetch_all_feeds_for_a_real_provider():
    provider = _first_provider_with_auto_discovery_url()

    _, gbfs_payload = fetch_gbfs(provider["Auto-Discovery URL"])
    feeds = parse_feeds(gbfs_payload)

    assert feeds

    for feed in feeds:
        last_updated, payload = fetch_feed(feed)

        assert last_updated is not None
        assert "data" in payload
