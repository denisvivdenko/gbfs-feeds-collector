import json
from datetime import datetime, timezone

import httpx
from pydantic import AnyHttpUrl, TypeAdapter

from gbfs_feeds_collector.crawlers.crawler_exceptions import (
    DownloadError,
    JSONFormatError,
    MissingLastUpdatedError,
)

LAST_UPDATED_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


async def fetch_gbfs_entity(client: httpx.AsyncClient, url: str) -> tuple[datetime, dict]:
    validated_url = _URL_ADAPTER.validate_python(url)

    try:
        response = await client.get(str(validated_url))
        response.raise_for_status()
        raw_body = response.content
    except httpx.HTTPError as error:
        raise DownloadError(f"Failed to download GBFS entity from {url}: {error}") from error

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as error:
        raise JSONFormatError(
            f"GBFS entity at {url} did not return valid JSON: {error}"
        ) from error

    raw_last_updated = payload.get("last_updated")
    try:
        last_updated = datetime.strptime(
            raw_last_updated, LAST_UPDATED_FORMAT
        ).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as error:
        raise MissingLastUpdatedError(
            f"GBFS entity at {url} has an invalid 'last_updated' value "
            f"{raw_last_updated!r}: {error}"
        ) from error

    return last_updated, payload
