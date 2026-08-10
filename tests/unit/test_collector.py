import copy
import logging

import pytest

from gbfs_feeds_collector.collector import (
    Feed,
    FeedsIndex,
    VersionError,
    parse_feeds_response,
)

VALID_PAYLOAD = {
    "last_updated": "2026-08-10T09:59:02Z",
    "ttl": 30,
    "data": {
        "feeds": [
            {
                "name": "gbfs_versions",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/gbfs_versions",
            },
            {
                "name": "geofencing_zones",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/geofencing_zones",
            },
            {
                "name": "station_information",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/station_information",
            },
            {
                "name": "station_status",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/station_status",
            },
            {
                "name": "system_information",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/system_information",
            },
            {
                "name": "system_pricing_plans",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/system_pricing_plans",
            },
            {
                "name": "system_regions",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/system_regions",
            },
            {
                "name": "vehicle_types",
                "url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/vehicle_types",
            },
        ]
    },
    "version": "3.0",
}


@pytest.fixture
def valid_payload():
    return copy.deepcopy(VALID_PAYLOAD)


def test_parse_feeds_response_returns_feeds_index_with_all_feeds(valid_payload):
    result = parse_feeds_response(valid_payload)

    assert isinstance(result, FeedsIndex)
    assert result.version == "3.0"
    assert result.ttl == 30
    assert result.last_updated == "2026-08-10T09:59:02Z"
    assert len(result.feeds) == 8
    assert all(isinstance(feed, Feed) for feed in result.feeds)
    assert result.feeds[0].name == "gbfs_versions"
    assert str(result.feeds[0].url) == (
        "https://careem.publicbikesystem.net/customer/gbfs/v3.0/gbfs_versions"
    )


def test_parse_feeds_response_does_not_force_a_specific_set_of_feed_names(valid_payload):
    valid_payload["data"]["feeds"] = [
        {"name": "some_unlisted_feed", "url": "https://example.com/some_unlisted_feed"}
    ]

    result = parse_feeds_response(valid_payload)

    assert len(result.feeds) == 1
    assert result.feeds[0].name == "some_unlisted_feed"


def test_parse_feeds_response_raises_version_error_on_mismatched_version(valid_payload):
    valid_payload["version"] = "2.3"

    with pytest.raises(VersionError) as exc_info:
        parse_feeds_response(valid_payload)

    assert "2.3" in str(exc_info.value)
    assert "3.0" in str(exc_info.value)


def test_parse_feeds_response_accepts_custom_expected_version(valid_payload):
    valid_payload["version"] = "2.3"

    result = parse_feeds_response(valid_payload, expected_version="2.3")

    assert result.version == "2.3"


def test_parse_feeds_response_raises_when_data_key_is_missing(valid_payload):
    del valid_payload["data"]

    with pytest.raises(ValueError):
        parse_feeds_response(valid_payload)


def test_parse_feeds_response_raises_when_feeds_key_is_missing(valid_payload):
    del valid_payload["data"]["feeds"]

    with pytest.raises(ValueError):
        parse_feeds_response(valid_payload)


def test_parse_feeds_response_skips_feed_with_invalid_url_and_logs_error(valid_payload, caplog):
    valid_payload["data"]["feeds"].append(
        {"name": "broken_feed", "url": "not-a-valid-url"}
    )

    with caplog.at_level(logging.ERROR, logger="gbfs_feeds_collector.collector"):
        result = parse_feeds_response(valid_payload)

    assert len(result.feeds) == 8
    assert "broken_feed" not in {feed.name for feed in result.feeds}
    assert any(
        record.levelno == logging.ERROR and "broken_feed" in record.message
        for record in caplog.records
    )


def test_parse_feeds_response_skips_feed_missing_name_and_logs_error(valid_payload, caplog):
    valid_payload["data"]["feeds"].append(
        {"url": "https://careem.publicbikesystem.net/customer/gbfs/v3.0/unnamed"}
    )

    with caplog.at_level(logging.ERROR, logger="gbfs_feeds_collector.collector"):
        result = parse_feeds_response(valid_payload)

    assert len(result.feeds) == 8
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_parse_feeds_response_skips_feed_missing_url_and_logs_error(valid_payload, caplog):
    valid_payload["data"]["feeds"].append({"name": "no_url_feed"})

    with caplog.at_level(logging.ERROR, logger="gbfs_feeds_collector.collector"):
        result = parse_feeds_response(valid_payload)

    assert len(result.feeds) == 8
    assert "no_url_feed" not in {feed.name for feed in result.feeds}
    assert any(
        record.levelno == logging.ERROR and "no_url_feed" in record.message
        for record in caplog.records
    )


def test_parse_feeds_response_returns_empty_feeds_list_when_all_feeds_invalid(caplog):
    payload = {
        "last_updated": "2026-08-10T09:59:02Z",
        "ttl": 30,
        "data": {"feeds": [{"name": "broken"}, {"url": "https://example.com/x"}]},
        "version": "3.0",
    }

    with caplog.at_level(logging.ERROR, logger="gbfs_feeds_collector.collector"):
        result = parse_feeds_response(payload)

    assert result.feeds == []
    assert len(caplog.records) == 2


def test_parse_feeds_response_raises_version_error_before_touching_feeds(valid_payload):
    valid_payload["version"] = "2.3"
    valid_payload["data"]["feeds"].append({"name": "broken"})

    with pytest.raises(VersionError):
        parse_feeds_response(valid_payload)
