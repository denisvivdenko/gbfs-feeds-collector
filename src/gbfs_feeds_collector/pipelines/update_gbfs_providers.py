import argparse
from pathlib import Path

from gbfs_feeds_collector.crawlers.gbfs_providers_crawler import fetch_gbfs_providers
from gbfs_feeds_collector.settings import settings


def update_gbfs_providers(output_path: Path = settings.gbfs_providers_csv_path) -> Path:
    data = fetch_gbfs_providers()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return output_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl the GBFS providers index and save it as a CSV file."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=settings.gbfs_providers_csv_path,
        help=f"Path to write the providers CSV to (default: {settings.gbfs_providers_csv_path}).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    update_gbfs_providers(args.output_path)


if __name__ == "__main__":
    main()
