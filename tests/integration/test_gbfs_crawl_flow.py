import csv

from gbfs_feeds_collector.crawlers.gbfs_entity_crawler import fetch_gbfs_entity
from gbfs_feeds_collector.parsers import parse_feeds
from gbfs_feeds_collector.settings import settings


def _first_provider_with_auto_discovery_url():
    with settings.gbfs_providers_csv_path.open(newline="", encoding="utf-8") as providers_file:
        for row in csv.DictReader(providers_file):
            if row["Auto-Discovery URL"]:
                return row
    raise AssertionError("No provider with an Auto-Discovery URL found")


def test_crawl_gbfs_parse_feeds_and_fetch_all_feeds_for_a_real_provider():
    provider = _first_provider_with_auto_discovery_url()

    _, gbfs_payload = fetch_gbfs_entity(provider["Auto-Discovery URL"])
    feeds = parse_feeds(gbfs_payload)

    assert feeds

    for feed in feeds:
        last_updated, payload = fetch_gbfs_entity(str(feed.url))

        assert last_updated is not None
        assert "data" in payload
