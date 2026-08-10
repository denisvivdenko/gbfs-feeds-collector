from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GBFS_")

    gbfs_providers_csv_path: Path = REPO_ROOT / "data" / "gbfs_providers.csv"
    gbfs_feeds_dir: Path = REPO_ROOT / "data" / "gbfs_feeds"


settings = Settings()
