from gbfs_feeds_collector.load_feeds_index import (
    fetch_feeds_index,
    save_feeds_index,
    validate_feeds_index,
)


def test_fetch_feeds_index_returns_real_data():
    data = fetch_feeds_index()

    validate_feeds_index(data)
    assert len(data) > 0


def test_save_feeds_index_writes_fetched_data_to_disk(tmp_path):
    output_path = tmp_path / "gbfs_feeds_index.csv"
    data = fetch_feeds_index()

    save_feeds_index(data, output_path)

    assert output_path.read_bytes() == data
