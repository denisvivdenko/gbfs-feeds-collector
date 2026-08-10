import csv
import io
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/MobilityData/gbfs/master/systems.csv"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "gbfs_feeds_index.csv"

EXPECTED_HEADER = [
    "Country Code",
    "Name",
    "Location",
    "System ID",
    "URL",
    "Auto-Discovery URL",
    "Supported Versions",
    "Authentication Info URL",
    "Authentication Type",
    "Authentication Parameter Name",
]


def fetch_feeds_index(url: str = URL) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def validate_feeds_index(data: bytes) -> None:
    header = next(csv.reader(io.StringIO(data.decode("utf-8"))))
    if header != EXPECTED_HEADER:
        raise ValueError(f"Unexpected GBFS feeds index header: {header}")


def save_feeds_index(data: bytes, output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)


def main() -> None:
    data = fetch_feeds_index()
    validate_feeds_index(data)
    save_feeds_index(data)


if __name__ == "__main__":
    main()
