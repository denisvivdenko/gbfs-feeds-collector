from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def list_keys(self, prefix: str) -> list[str]: ...


class LocalFileSystemStorage:
    def __init__(self, root: Path):
        self.root = root

    def save(self, key: str, data: bytes) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def list_keys(self, prefix: str) -> list[str]:
        prefix_path = self.root / prefix
        if not prefix_path.is_dir():
            return []
        return sorted(
            str(path.relative_to(self.root))
            for path in prefix_path.rglob("*")
            if path.is_file()
        )
