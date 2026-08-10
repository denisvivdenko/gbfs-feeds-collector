import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from pydantic import AnyHttpUrl, TypeAdapter

from gbfs_feeds_collector.crawler_exceptions import (
    DateError,
    DownloadError,
    JSONFormatError,
)
from gbfs_feeds_collector.feed_crawler import LAST_UPDATED_FORMAT

_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


def fetch_gbfs(url: str) -> tuple[datetime, dict]:
    validated_url = _URL_ADAPTER.validate_python(url)

    try:
        with urllib.request.urlopen(str(validated_url)) as response:
            raw_body = response.read()
    except (urllib.error.URLError, OSError) as error:
        raise DownloadError(
            f"Failed to download GBFS feed from {url}: {error}"
        ) from error

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise JSONFormatError(
            f"GBFS feed at {url} did not return valid JSON: {error}"
        ) from error

    raw_last_updated = payload.get("last_updated")
    try:
        last_updated = datetime.strptime(
            raw_last_updated, LAST_UPDATED_FORMAT
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as error:
        raise DateError(
            f"GBFS feed at {url} has an invalid 'last_updated' value "
            f"{raw_last_updated!r}: {error}"
        ) from error

    return last_updated, payload
