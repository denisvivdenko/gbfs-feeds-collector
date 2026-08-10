import logging

from pydantic import AnyHttpUrl, ValidationError
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)


class VersionError(Exception):
    pass


@dataclass
class Feed:
    name: str
    url: AnyHttpUrl


@dataclass
class FeedsIndex:
    version: str
    last_updated: str
    ttl: int
    feeds: list[Feed]


def parse_feeds_response(payload: dict, expected_version: str = "3.0") -> FeedsIndex:
    version = payload.get("version")
    if version != expected_version:
        raise VersionError(
            f"Unsupported GBFS version: expected {expected_version!r}, got {version!r}"
        )

    if "data" not in payload:
        raise ValueError("GBFS payload is missing the 'data' key")
    if "feeds" not in payload["data"]:
        raise ValueError("GBFS payload is missing the 'data' -> 'feeds' key")

    feeds = []
    for raw_feed in payload["data"]["feeds"]:
        try:
            feeds.append(Feed(**raw_feed))
        except (ValidationError, TypeError) as error:
            logger.error("Failed to parse GBFS feed %r: %s", raw_feed, error)

    return FeedsIndex(
        version=version,
        last_updated=payload.get("last_updated"),
        ttl=payload.get("ttl"),
        feeds=feeds,
    )
