import boto3
import pytest
from moto import mock_aws

from gbfs_feeds_collector.storage import S3Storage

BUCKET = "gbfs-feeds-collector-test"


@pytest.fixture
def storage():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield S3Storage(BUCKET, client=client)


def test_save_then_read_returns_the_same_bytes(storage):
    storage.save("provider/feed/2026-08-10T11:38:42Z.json", b'{"data": {}}')

    assert storage.read("provider/feed/2026-08-10T11:38:42Z.json") == b'{"data": {}}'


def test_list_keys_returns_keys_under_prefix(storage):
    storage.save("provider/system_information/2026-08-10T11:38:42Z.json", b"{}")
    storage.save("provider/vehicle_types/2026-08-10T11:39:00Z.json", b"{}")
    storage.save("other-provider/system_information/2026-08-10T11:38:42Z.json", b"{}")

    keys = storage.list_keys("provider")

    assert keys == [
        "provider/system_information/2026-08-10T11:38:42Z.json",
        "provider/vehicle_types/2026-08-10T11:39:00Z.json",
    ]


def test_list_keys_returns_empty_list_when_prefix_does_not_exist(storage):
    assert storage.list_keys("missing-provider") == []
