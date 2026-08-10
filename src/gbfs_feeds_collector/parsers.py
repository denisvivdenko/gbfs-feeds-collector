from pydantic import AnyHttpUrl, BaseModel


class Feed(BaseModel):
    name: str
    url: AnyHttpUrl


def parse_feeds(payload: dict) -> list[Feed]:
    return [Feed(name=feed["name"], url=feed["url"]) for feed in payload["data"]["feeds"]]
