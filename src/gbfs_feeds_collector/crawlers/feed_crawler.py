import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pydantic import AnyHttpUrl, BaseModel

from gbfs_feeds_collector.crawlers.crawler_exceptions import (
    DateError,
    DownloadError,
    JSONFormatError,
)


LAST_UPDATED_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class Feed(BaseModel):
    name: str
    url: AnyHttpUrl


def fetch_feed(feed: Feed) -> tuple[datetime, dict]:
    try:
        with urllib.request.urlopen(str(feed.url)) as response:
            raw_body = response.read()
    except (urllib.error.URLError, OSError) as error:
        raise DownloadError(
            f"Failed to download feed {feed.name!r} from {feed.url}: {error}"
        ) from error

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise JSONFormatError(
            f"Feed {feed.name!r} at {feed.url} did not return valid JSON: {error}"
        ) from error

    raw_last_updated = payload.get("last_updated")
    try:
        last_updated = datetime.strptime(
            raw_last_updated, LAST_UPDATED_FORMAT
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as error:
        raise DateError(
            f"Feed {feed.name!r} at {feed.url} has an invalid 'last_updated' value "
            f"{raw_last_updated!r}: {error}"
        ) from error

    return last_updated, payload
