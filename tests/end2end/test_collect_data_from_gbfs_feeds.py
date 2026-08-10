import json
import subprocess
import sys

from gbfs_feeds_collector.parsers import parse_providers
from gbfs_feeds_collector.settings import settings
from gbfs_feeds_collector.storage import LocalFileSystemStorage


def test_collect_data_from_gbfs_feeds_script_saves_raw_feeds_under_provider_and_feed_name(
    tmp_path,
):
    output_path = tmp_path / "gbfs_feeds"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gbfs_feeds_collector.pipelines.collect_data_from_gbfs_feeds",
            "--output-path",
            str(output_path),
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    providers = parse_providers(settings.gbfs_providers_csv_path.read_bytes())
    provider = providers[0]

    storage = LocalFileSystemStorage(output_path)
    keys = storage.list_keys(provider.id)
    assert keys

    for key in keys:
        provider_id, feed_name, file_name = key.split("/")
        assert provider_id == provider.id
        assert feed_name
        assert file_name.endswith(".json")

        payload = json.loads(storage.read(key))
        assert "data" in payload
