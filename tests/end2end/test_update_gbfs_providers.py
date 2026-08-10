import csv
import subprocess
import sys

from gbfs_feeds_collector.crawlers.gbfs_providers_crawler import EXPECTED_HEADER


def test_update_gbfs_providers_script_crawls_providers_into_output_path(tmp_path):
    output_path = tmp_path / "gbfs_providers.csv"
    assert not output_path.exists()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gbfs_feeds_collector.pipelines.update_gbfs_providers",
            "--output-path",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.exists()

    with output_path.open(newline="", encoding="utf-8") as providers_file:
        rows = list(csv.reader(providers_file))

    assert rows[0] == EXPECTED_HEADER
    assert len(rows) > 1
