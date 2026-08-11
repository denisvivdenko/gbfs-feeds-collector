import pytest
from pydantic import ValidationError

from gbfs_feeds_collector.feed_schedule import load_feed_schedule


def test_load_feed_schedule_parses_feed_name_to_interval_seconds(tmp_path):
    path = tmp_path / "feeds_schedule.yaml"
    path.write_text(
        "station_status: 30\n"
        "station_information: 3600\n"
    )

    schedule = load_feed_schedule(path)

    assert schedule == {"station_status": 30, "station_information": 3600}


def test_load_feed_schedule_raises_on_missing_file(tmp_path):
    path = tmp_path / "does_not_exist.yaml"

    with pytest.raises(FileNotFoundError):
        load_feed_schedule(path)


def test_load_feed_schedule_raises_on_non_mapping_yaml(tmp_path):
    path = tmp_path / "feeds_schedule.yaml"
    path.write_text("- station_status\n- station_information\n")

    with pytest.raises(ValidationError):
        load_feed_schedule(path)


@pytest.mark.parametrize("bad_interval", [0, -30, "not-a-number"])
def test_load_feed_schedule_raises_on_non_positive_interval(tmp_path, bad_interval):
    path = tmp_path / "feeds_schedule.yaml"
    path.write_text(f"station_status: {bad_interval!r}\n")

    with pytest.raises(ValidationError):
        load_feed_schedule(path)


def test_load_feed_schedule_returns_empty_dict_for_empty_file(tmp_path):
    path = tmp_path / "feeds_schedule.yaml"
    path.write_text("")

    assert load_feed_schedule(path) == {}
