import os
import re
from pathlib import Path


RECEIPTS_ROOT = Path("data") / "receipts"


def _sanitize_profile_name(profile: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", profile or "")
    safe = safe.strip("._-")
    return safe or "default"


def _default_db_path() -> str:
    profile = _sanitize_profile_name(os.environ.get("DB_PROFILE", "default"))
    if profile == "default":
        return "data/accounting.db"
    return f"data/accounting_{profile}.db"


def _sqlite_path_from_env() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    if database_url.startswith("sqlite:///"):
        return database_url[len("sqlite:///"):]
    return os.environ.get("DB_PATH", _default_db_path())


def get_db_folder_name() -> str:
    db_path = _sqlite_path_from_env()
    db_name = Path(db_path).name
    stem = Path(db_name).stem or "default"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return safe or "default"


def get_receipts_root() -> Path:
    RECEIPTS_ROOT.mkdir(parents=True, exist_ok=True)
    return RECEIPTS_ROOT


def get_receipts_dir_for_year(year: int) -> Path:
    target = get_receipts_root() / get_db_folder_name() / str(year)
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_receipt_relative_path(filename: str, year: int) -> str:
    return f"{get_db_folder_name()}/{year}/{filename}".replace("\\", "/")
