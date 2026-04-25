# REST API Examples

These are curl examples for the Accounting Application REST API.

> **Note:** Application runs at `http://127.0.0.1:8000`  
> Swagger API documentation: `http://127.0.0.1:8000/docs`

---

## Cost Centers

### Create New Cost Center

```bash
curl -X POST http://127.0.0.1:8000/cost-centers/new \
  -d "name=Pääasunto" \
  -d "type=apartment" \
  -d "vat_deductible=on"
```

### List Cost Centers

```bash
curl http://127.0.0.1:8000/cost-centers/
```

---

## Categories (Expense Categories)

### Create New Expense Category

```bash
curl -X POST http://127.0.0.1:8000/categories/new \
  -d "name=Siivous" \
  -d "category_type=expense"
```

### Create Income Category

```bash
curl -X POST http://127.0.0.1:8000/categories/new \
  -d "name=Vuokra" \
  -d "category_type=income"
```

### List Categories

```bash
curl http://127.0.0.1:8000/categories/
```

---

## Expenses (Expenses)

### List All Expenses

```bash
curl http://127.0.0.1:8000/expenses/
```

### List Expenses by Cost Center

```bash
curl "http://127.0.0.1:8000/expenses/?cost_center_id=1"
```

### List Expenses for Year 2026

```bash
curl "http://127.0.0.1:8000/expenses/?year=2026"
```

### Create Single-Line Expense

```bash
curl -X POST http://127.0.0.1:8000/expenses/new \
  -d "cost_center_id=1" \
  -d "date=2026-04-26" \
  -d "description=Pyykinpesu" \
  -d "entry_type=expense" \
  -d "line_category_id[]=1" \
  -d "line_description[]=Pyykinpesu" \
  -d "line_gross_amount[]=120" \
  -d "line_vat_rate[]=24"
```

### Create Multi-Line Expense (2 riviä)

```bash
curl -X POST http://127.0.0.1:8000/expenses/new \
  -d "cost_center_id=1" \
  -d "date=2026-04-26" \
  -d "description=Huoltopalvelu" \
  -d "entry_type=expense" \
  -d "line_category_id[]=1" \
  -d "line_category_id[]=2" \
  -d "line_description[]=Pyykinpesu" \
  -d "line_description[]=Korjaustöö" \
  -d "line_gross_amount[]=120" \
  -d "line_gross_amount[]=80" \
  -d "line_vat_rate[]=24" \
  -d "line_vat_rate[]=24"
```

### Create Expense with Receipt File

```bash
curl -X POST http://127.0.0.1:8000/expenses/new \
  -F "cost_center_id=1" \
  -F "date=2026-04-26" \
  -F "entry_type=expense" \
  -F "line_category_id[]=1" \
  -F "line_description[]=Siivous" \
  -F "line_gross_amount[]=150" \
  -F "line_vat_rate[]=24" \
  -F "receipt_image=@receipt.pdf"
```

### Edit Existing Expense

```bash
curl -X POST http://127.0.0.1:8000/expenses/1/edit \
  -d "cost_center_id=1" \
  -d "date=2026-04-27" \
  -d "description=Päivitetty kuvaus" \
  -d "entry_type=expense" \
  -d "line_category_id[]=1" \
  -d "line_description[]=Päivitetty siivous" \
  -d "line_gross_amount[]=160" \
  -d "line_vat_rate[]=24"
```

### Delete Expense

```bash
curl -X POST http://127.0.0.1:8000/expenses/1/delete
```

---

## Reports (Reports)

### Get Annual Report

```bash
curl "http://127.0.0.1:8000/reports/yearly?cost_center_id=1&year=2026"
```

### Export as CSV

```bash
curl "http://127.0.0.1:8000/reports/yearly/csv?cost_center_id=1&year=2026" \
  --output report.csv
```

---

## Python Examples

### Using requests Library

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# Luo kategoria
resp = requests.post(f"{BASE_URL}/categories/new", data={
    "name": "Siivous",
    "category_type": "expense"
})
print(f"Status: {resp.status_code}")

# Luo tapahtuma
resp = requests.post(f"{BASE_URL}/expenses/new", data={
    "cost_center_id": 1,
    "date": "2026-04-26",
    "entry_type": "expense",
    "line_category_id[]": [1],
    "line_description[]": ["Pyykinpesu"],
    "line_gross_amount[]": [120],
    "line_vat_rate[]": [24]
})
print(f"Redirect to: {resp.history[-1].headers['location']}")

# Listaa tapahtumat
resp = requests.get(f"{BASE_URL}/expenses/", params={
    "cost_center_id": 1,
    "year": 2026
})
print(resp.text)
```

### Get Report

```python
import requests
import json

resp = requests.get("http://127.0.0.1:8000/reports/yearly", params={
    "cost_center_id": 1,
    "year": 2026
})

# HTML-sivu, joten tarvitset HTML-parserin
from bs4 import BeautifulSoup
soup = BeautifulSoup(resp.text, 'html.parser')

# Etsi taulukko
table = soup.find("table")
print(table.text)
```

---

## JavaScript Examples

### Get Report with JavaScript

```javascript
async function getYearlyReport(costCenterId, year) {
    const url = `/reports/yearly?cost_center_id=${costCenterId}&year=${year}`;
    const response = await fetch(url);
    const html = await response.text();
    
    // Parse HTML ja etsi data taulukosta
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const table = doc.querySelector('table');
    
    console.log(table.innerText);
}

// Käytä
getYearlyReport(1, 2026);
```

### Create Expense

```javascript
async function createExpense() {
    const formData = new FormData();
    formData.append('cost_center_id', '1');
    formData.append('date', '2026-04-26');
    formData.append('entry_type', 'expense');
    formData.append('line_category_id[]', '1');
    formData.append('line_description[]', 'Siivous');
    formData.append('line_gross_amount[]', '120');
    formData.append('line_vat_rate[]', '24');
    
    const response = await fetch('/expenses/new', {
        method: 'POST',
        body: formData
    });
    
    console.log(response.status);
}
```

---

## Batch Scripts (PowerShell)

### Create Category

```powershell
$params = @{
    Uri = "http://127.0.0.1:8000/categories/new"
    Method = "POST"
    Body = @{
        name = "Siivous"
        category_type = "expense"
    }
}

$response = Invoke-WebRequest @params
Write-Host "Status: $($response.StatusCode)"
```

### List Expenses

```powershell
$response = Invoke-WebRequest `
    -Uri "http://127.0.0.1:8000/expenses/?cost_center_id=1&year=2026" `
    -UseBasicParsing

$html = $response.Content
# Etsi taulukko regex:lla tai HTML-parserilla
if ($html -match "<table") {
    Write-Host "Taulu löytyi"
}
```

---

## Swagger/OpenAPI

Automatic API documentation:

```
http://127.0.0.1:8000/docs
```

Here you can:
- See all routes
- Test the API directly
- View parameters and responses
- Download OpenAPI JSON schema

---

## Error Handling

### Not Found

```
Status: 404
Body: {"detail": "Not found"}
```

### Validation Error

```
Status: 422
Body: {"detail": [{"loc": ["body", "field"], "msg": "..."}]}
```

### Server Error

```
Status: 500
Body: {"detail": "Internal server error"}
```

---

## Testing Guidelines

### Unit Testing (pytest)

```bash
pytest tests/test_models.py -v
pytest tests/test_expenses_api.py -v
```

### Integration Testing

```bash
python -m pytest tests/test_integration.py --tb=short
```

### Load Testing (locust)

```bash
locust -f locustfile.py --host=http://127.0.0.1:8000
```

---

**API Version:** 1.0  
**Updated:** April 26, 2026
