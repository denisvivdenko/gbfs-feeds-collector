from gbfs_feeds_collector.feed_crawler import Feed


def parse_feeds(payload: dict) -> list[Feed]:
    return [Feed(name=feed["name"], url=feed["url"]) for feed in payload["data"]["feeds"]]
