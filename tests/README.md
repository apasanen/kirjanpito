# Running Tests

The Accounting Application includes unit tests and integration tests using the pytest framework.

---

## 📋 Prerequisites

### 1. Install Test Dependencies

```bash
# Activate virtual environment first
.venv\Scripts\Activate.ps1

# Install new packages
pip install pytest pytest-asyncio httpx
```

Or update all requirements:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running Tests

### All Tests

```bash
pytest
```

### Verbose Output

```bash
pytest -v
```

### Specific Test File

```bash
pytest tests/test_models.py
pytest tests/test_api.py
```

### Specific Test Function

```bash
pytest tests/test_models.py::TestCostCenterModel::test_create_cost_center -v
```

### Real-Time Output

```bash
pytest -s
```

### Tests with Coverage

```bash
pip install pytest-cov
pytest --cov=app tests/
```

### Tests with Coverage HTML-raportti

```bash
pytest --cov=app --cov-report=html tests/
# Open htmlcov/index.html in browser
```

---

## 📁 Test File Structure

| File | Contents |
|----------|---------|
| **tests/conftest.py** | Pytest fixtures (test_db, client, db_session) |
| **tests/test_models.py** | Unit tests SQLAlchemy-malleille |
| **tests/test_api.py** | Integration tests REST API:lle |
| **tests/__init__.py** | Python package marker |

---

## 🔬 Tests Overview

### test_models.py

- ✅ `TestCostCenterModel` – Kustannuspaikan luonti ja relaatiot
- ✅ `TestExpenseCategoryModel` – Kategorioiden luonti ja composite unique
- ✅ `TestExpenseModel` – Tapahtuman luonti ja cascade delete
- ✅ `TestExpenseLineModel` – Rivin luonti ja multi-line tapahtumat

### test_api.py

- ✅ `TestCostCentersAPI` – /cost_centers/ -päätepiste
- ✅ `TestCategoriesAPI` – /categories/ -päätepiste
- ✅ `TestExpensesAPI` – /expenses/ -päätepisteen luonti
- ✅ `TestReportsAPI` – /reports/yearly -raportti

---

## 🛠️ Examples

### Run All Tests and Show Failed Tests

```bash
pytest --tb=short
```

### Run Tests Containing "expense" Word

```bash
pytest -k expense -v
```

### Run First 3 Failed Tests and Stop

```bash
pytest --maxfail=3
```

### Run Tests in Parallel (requires pytest-xdist)

```bash
pip install pytest-xdist
pytest -n 4
```

---

## 📊 Example Test Output

### Successful Tests

```
tests/test_models.py::TestCostCenterModel::test_create_cost_center PASSED
```

### Failed Tests

```
tests/test_api.py::TestExpensesAPI::test_create_simple_expense FAILED
```

### Skipped Tests

```
tests/test_api.py::TestReportsAPI::test_yearly_report SKIPPED
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'pytest'"

```bash
pip install pytest pytest-asyncio
```

### "FAILED ... ImportError: cannot import name 'get_db' from app.database"

Check that `app/database.py` has a `get_db` function.

### Tests Hang (timeout)

```bash
pytest --timeout=10  # 10 sekunnin timeout
```

Install pytest-timeout:

```bash
pip install pytest-timeout
```

### "RuntimeError: Event loop is closed"

Use `pytest-asyncio`:

```bash
pip install pytest-asyncio
```

---

## 💡 Writing New Tests

### Template

```python
def test_new_feature(client, db_session):
    """Test description."""
    
    # 1. Setup - create and prepare
    center = CostCenter(name="Test", type="apartment", vat_deductible=True)
    db_session.add(center)
    db_session.commit()
    
    # 2. Action - execute test action
    response = client.get("/cost_centers/")
    
    # 3. Assert - verify results
    assert response.status_code == 200
    assert "Test" in response.text
```

### Using Fixtures

```python
def test_example(client, db_session, test_receipts_dir):
    """Use multiple fixtures."""
    # client - FastAPI test client
    # db_session - database session with seed data
    # test_receipts_dir - temporary directory for files
    pass
```

---

## 🚀 Windows Batch Script for Running Tests

Created `run-tests.bat`:

```batch
@echo off
setlocal enabledelayedexpansion

echo === Installing test dependencies ===
call .venv\Scripts\pip install pytest pytest-asyncio httpx

echo.
echo === Running all tests ===
call .venv\Scripts\pytest -v

if %ERRORLEVEL% neq 0 (
    echo.
    echo === Some tests failed ===
    exit /b 1
)

echo.
echo === All tests passed ===
exit /b 0
```

---

## 📈 CI/CD Integration (GitHub Actions)

File `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run tests
      run: pytest -v
```

---

**Updated:** April 26, 2026
