import os
import re
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _sanitize_profile_name(profile: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", profile or "")
    safe = safe.strip("._-")
    return safe or "default"


def _default_db_path() -> Path:
    profile = _sanitize_profile_name(os.environ.get("DB_PROFILE", "default"))
    if profile == "default":
        return Path("data") / "accounting.db"
    return Path("data") / f"accounting_{profile}.db"


def _get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    db_path = Path(os.environ.get("DB_PATH", str(_default_db_path())))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.is_absolute():
        return f"sqlite:///{db_path.as_posix()}"
    return f"sqlite:///./{db_path.as_posix()}"


DATABASE_URL = _get_database_url()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401 – ensures models are registered
    Base.metadata.create_all(bind=engine)
    # Migrate: add reference column if it doesn't exist yet
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN reference VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass  # Column already exists
        try:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN entry_type VARCHAR(10) NOT NULL DEFAULT 'expense'"))
            conn.commit()
        except Exception:
            pass  # Column already exists
        try:
            conn.execute(text("ALTER TABLE expense_categories ADD COLUMN category_type VARCHAR(10) NOT NULL DEFAULT 'expense'"))
            conn.commit()
        except Exception:
            pass  # Column already exists
        try:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN no_receipt BOOLEAN NOT NULL DEFAULT 0"))
            conn.commit()
        except Exception:
            pass  # Column already exists
        _migrate_category_unique_name_type(conn)
        # apartment_year_settings is created by create_all if it doesn't exist
        _migrate_to_expense_lines(conn)


def _migrate_to_expense_lines(conn):
    """One-time migration: move expense amounts into expense_lines table."""
    # Check if expense_lines table exists (created by create_all before this runs)
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_lines'"))
    if not result.fetchone():
        return  # Not yet created

    # Check if expenses still has the old gross_amount column
    result = conn.execute(text("PRAGMA table_info(expenses)"))
    columns = {row[1] for row in result.fetchall()}
    if "gross_amount" not in columns:
        return  # Already migrated

    # Migrate each expense without existing lines to a single ExpenseLine
    result = conn.execute(text("""
        SELECT e.id, e.category_id, e.description, e.gross_amount, e.vat_rate, e.vat_amount, e.net_amount
        FROM expenses e
        WHERE NOT EXISTS (SELECT 1 FROM expense_lines el WHERE el.expense_id = e.id)
    """))
    rows = result.fetchall()
    for row in rows:
        exp_id, cat_id, desc, gross, vat_rate, vat_amount, net = row
        conn.execute(text("""
            INSERT INTO expense_lines (expense_id, category_id, description, gross_amount, vat_rate, vat_amount, net_amount, sort_order)
            VALUES (:eid, :cid, :desc, :gross, :vr, :va, :na, 0)
        """), {"eid": exp_id, "cid": cat_id, "desc": desc or "",
               "gross": str(gross), "vr": str(vat_rate), "va": str(vat_amount), "na": str(net)})
    conn.commit()

    # Recreate expenses table without the old amount columns
    conn.execute(text("ALTER TABLE expenses RENAME TO expenses_v1"))
    conn.execute(text("""
        CREATE TABLE expenses (
            id INTEGER NOT NULL PRIMARY KEY,
            reference VARCHAR(20) UNIQUE,
            entry_type VARCHAR(10) NOT NULL DEFAULT 'expense',
            cost_center_id INTEGER NOT NULL REFERENCES cost_centers(id),
            date DATE NOT NULL,
            description VARCHAR(255) NOT NULL DEFAULT '',
            notes TEXT,
            receipt_image_path VARCHAR(500),
            no_receipt BOOLEAN NOT NULL DEFAULT 0,
            drive_file_id VARCHAR(200),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    # Deduplicate references before inserting (make duplicate references NULL)
    conn.execute(text("""
        UPDATE expenses_v1 SET reference = NULL
        WHERE id NOT IN (
            SELECT MIN(id) FROM expenses_v1 WHERE reference IS NOT NULL GROUP BY reference
        ) AND reference IS NOT NULL
    """))
    has_no_receipt = "no_receipt" in columns
    if has_no_receipt:
        conn.execute(text("""
            INSERT INTO expenses (id, reference, entry_type, cost_center_id, date, description, notes,
                                  receipt_image_path, no_receipt, drive_file_id, created_at, updated_at)
            SELECT id, reference, entry_type, cost_center_id, date,
                   COALESCE(description, '') AS description, notes,
                   receipt_image_path, no_receipt, drive_file_id, created_at, updated_at
            FROM expenses_v1
        """))
    else:
        conn.execute(text("""
            INSERT INTO expenses (id, reference, entry_type, cost_center_id, date, description, notes,
                                  receipt_image_path, no_receipt, drive_file_id, created_at, updated_at)
            SELECT id, reference, entry_type, cost_center_id, date,
                   COALESCE(description, '') AS description, notes,
                   receipt_image_path, 0, drive_file_id, created_at, updated_at
            FROM expenses_v1
        """))
    conn.execute(text("DROP TABLE expenses_v1"))
    try:
        conn.execute(text("CREATE UNIQUE INDEX ix_expenses_reference ON expenses(reference)"))
    except Exception:
        pass
    conn.commit()


def _migrate_category_unique_name_type(conn):
    """Ensure expense_categories uniqueness is on (name, category_type), not name only."""
    table_sql = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='expense_categories'"))
    row = table_sql.fetchone()
    if not row or not row[0]:
        return

    create_sql = row[0]
    normalized_sql = create_sql.replace("\n", " ").replace("\t", " ")

    # Already migrated if composite unique is present.
    if "UNIQUE (name, category_type)" in normalized_sql or "uq_expense_categories_name_type" in normalized_sql:
        return

    # Only migrate if legacy name-only unique exists.
    if "UNIQUE (name)" not in normalized_sql:
        return

    conn.execute(text("PRAGMA foreign_keys=OFF"))
    conn.execute(text("ALTER TABLE expense_categories RENAME TO expense_categories_v1"))
    conn.execute(text("""
        CREATE TABLE expense_categories (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            category_type VARCHAR(10) NOT NULL DEFAULT 'expense',
            CONSTRAINT uq_expense_categories_name_type UNIQUE (name, category_type)
        )
    """))
    conn.execute(text("""
        INSERT INTO expense_categories (id, name, category_type)
        SELECT id, name, category_type
        FROM expense_categories_v1
    """))
    conn.execute(text("DROP TABLE expense_categories_v1"))
    try:
        conn.execute(text("CREATE INDEX ix_expense_categories_name ON expense_categories(name)"))
    except Exception:
        pass
    conn.execute(text("PRAGMA foreign_keys=ON"))
    conn.commit()
