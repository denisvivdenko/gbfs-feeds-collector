from pathlib import Path

import yaml
from pydantic import PositiveInt, TypeAdapter

FeedSchedule = dict[str, int]

_SCHEDULE_ADAPTER = TypeAdapter(dict[str, PositiveInt])


def load_feed_schedule(path: Path) -> FeedSchedule:
    raw = yaml.safe_load(path.read_text()) or {}
    return _SCHEDULE_ADAPTER.validate_python(raw)
