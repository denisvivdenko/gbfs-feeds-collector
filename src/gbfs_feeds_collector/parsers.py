import csv
import io

from pydantic import AnyHttpUrl, BaseModel


class Feed(BaseModel):
    name: str
    url: AnyHttpUrl


class Provider(BaseModel):
    id: str
    name: str
    url: AnyHttpUrl


def parse_feeds(payload: dict) -> list[Feed]:
    return [Feed(name=feed["name"], url=feed["url"]) for feed in payload["data"]["feeds"]]


def parse_providers(csv_data: bytes) -> list[Provider]:
    rows = csv.DictReader(io.StringIO(csv_data.decode("utf-8")))
    return [
        Provider(id=row["System ID"], name=row["Name"], url=row["Auto-Discovery URL"])
        for row in rows
        if row["Auto-Discovery URL"]
    ]
