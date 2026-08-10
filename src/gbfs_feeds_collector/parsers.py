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
    supported_versions: list[str]


def parse_feeds(payload: dict) -> list[Feed]:
    return [Feed(name=feed["name"], url=feed["url"]) for feed in payload["data"]["feeds"]]


def parse_providers(csv_data: bytes) -> list[Provider]:
    rows = csv.DictReader(io.StringIO(csv_data.decode("utf-8")))
    return [
        Provider(
            id=row["System ID"],
            name=row["Name"],
            url=row["Auto-Discovery URL"],
            supported_versions=[
                version.strip()
                for version in row["Supported Versions"].split(";")
                if version.strip()
            ],
        )
        for row in rows
        if row["Auto-Discovery URL"]
    ]


def is_gbfs_v3_provider(provider: Provider) -> bool:
    return any(version.startswith("3") for version in provider.supported_versions)
