"""
Pytest configuration and fixtures for Kirjanpito-ohjelma tests.
"""

import os
import pytest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session

# Import models to register them with Base
from app.models import (
    CostCenter, ExpenseCategory, Expense, ExpenseLine, ApartmentYearSetting
)
from app.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient


# Create a module-level test database that persists for all tests
# Use file-based SQLite for persistence across test functions
TEST_DB_PATH = Path(tempfile.gettempdir()) / "kirjanpito_test.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Create all tables once at module load
Base.metadata.create_all(bind=engine)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override get_db dependency for testing."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Apply override at module load
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """FastAPI TestClient with test database."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Get a fresh database session for each test with clean data."""
    db = TestSessionLocal()
    
    # For unit tests, clean data before test
    # (API tests don't use this fixture and maintain global database state)
    db.execute(text("DELETE FROM expense_lines"))
    db.execute(text("DELETE FROM expenses"))
    db.execute(text("DELETE FROM apartment_year_settings"))
    db.execute(text("DELETE FROM cost_centers"))
    db.execute(text("DELETE FROM expense_categories"))
    db.commit()
    
    yield db
    
    # Clean up after test
    try:
        db.execute(text("DELETE FROM expense_lines"))
        db.execute(text("DELETE FROM expenses"))
        db.execute(text("DELETE FROM apartment_year_settings"))
        db.execute(text("DELETE FROM cost_centers"))
        db.execute(text("DELETE FROM expense_categories"))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


# Create a separate fixture for API tests that seeds initial data
@pytest.fixture(scope="function")
def api_db_session():
    """Database session for API tests with persistent data."""
    db = TestSessionLocal()
    
    # Seed initial data for API tests
    db.execute(text("DELETE FROM expense_lines"))
    db.execute(text("DELETE FROM expenses"))
    db.execute(text("DELETE FROM apartment_year_settings"))
    db.execute(text("DELETE FROM cost_centers"))
    db.execute(text("DELETE FROM expense_categories"))
    db.commit()
    
    # Add default data
    from app.models import CostCenter, ExpenseCategory
    
    center = CostCenter(
        name="Test Center",
        type="apartment",
        vat_deductible=True,
        description="Default test center"
    )
    db.add(center)
    
    categories = [
        ExpenseCategory(name="Siivous", category_type="expense"),
        ExpenseCategory(name="Korjaukset", category_type="expense"),
        ExpenseCategory(name="Kilometrikulut", category_type="expense"),
        ExpenseCategory(name="Vuokra", category_type="income"),
        ExpenseCategory(name="Muut", category_type="expense"),
    ]
    db.add_all(categories)
    db.commit()
    
    yield db
    
    # Cleanup after test
    try:
        db.execute(text("DELETE FROM expense_lines"))
        db.execute(text("DELETE FROM expenses"))
        db.execute(text("DELETE FROM apartment_year_settings"))
        db.execute(text("DELETE FROM cost_centers"))
        db.execute(text("DELETE FROM expense_categories"))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


@pytest.fixture
def test_receipts_dir():
    """Create a temporary directory for test receipts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
