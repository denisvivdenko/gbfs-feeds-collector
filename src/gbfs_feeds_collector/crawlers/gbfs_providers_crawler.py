import csv
import io
import urllib.request

URL = "https://raw.githubusercontent.com/MobilityData/gbfs/master/systems.csv"

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


def fetch_gbfs_providers(url: str = URL) -> bytes:
    with urllib.request.urlopen(url) as response:
        data = response.read()
        __validate(data)
        return data


def __validate(data: bytes) -> None:
    header = next(csv.reader(io.StringIO(data.decode("utf-8"))))
    if header != EXPECTED_HEADER:
        raise ValueError(f"Unexpected GBFS feeds index header: {header}")
