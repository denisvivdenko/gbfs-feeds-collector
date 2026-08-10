import pytest

from gbfs_feeds_collector.parsers import (
    Feed,
    Provider,
    is_gbfs_v3_provider,
    parse_feeds,
    parse_providers,
)


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


@pytest.fixture
def providers_csv():
    return (
        "Country Code,Name,Location,System ID,URL,Auto-Discovery URL,Supported Versions,"
        "Authentication Info URL,Authentication Type,Authentication Parameter Name\n"
        "AE,Careem BIKE,Dubai,careem_bike,https://www.careem.com/,"
        "https://careem.publicbikesystem.net/gbfs.json,3.0,,,\n"
        "US,No Discovery Provider,Somewhere,no-discovery,https://example.com/,,2.3,,,\n"
    ).encode("utf-8")


def test_parse_providers_returns_provider_objects_with_auto_discovery_url(providers_csv):
    providers = parse_providers(providers_csv)

    assert providers == [
        Provider(
            id="careem_bike",
            name="Careem BIKE",
            url="https://careem.publicbikesystem.net/gbfs.json",
            supported_versions=["3.0"],
        ),
    ]


def test_parse_providers_skips_rows_without_auto_discovery_url(providers_csv):
    providers = parse_providers(providers_csv)

    assert all(provider.id != "no-discovery" for provider in providers)
