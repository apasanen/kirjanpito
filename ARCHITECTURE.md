# Arkkitehtuuri ja Designin dokumentaatio

Tämä dokumentti selittää Kirjanpito-ohjelman sisäisen rakenteen ja suunnittelupäätökset.

---

## 1. Sovelluksen arkkitehtuuri

### 1.1 Kerrosrakenne

```
┌─────────────────────────────────────┐
│         Frontend (Browser)          │
│      HTML + Jinja2 + JavaScript     │
└──────────────────┬──────────────────┘
                   │ HTTP/REST
┌──────────────────▼──────────────────┐
│       FastAPI Web Server            │
│  (app/main.py, app/routers/*)       │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│      SQLAlchemy ORM Layer           │
│       (app/models.py)               │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│       SQLite Database               │
│      (accounting.db)                │
└─────────────────────────────────────┘
```

### 1.2 Moduulit

| Moduuli | Tiedosto | Vastuu |
|---------|----------|--------|
| Main app | `app/main.py` | FastAPI-sovellus, middleware, startup |
| Models | `app/models.py` | SQLAlchemy-mallit (ORM) |
| Database | `app/database.py` | Tietokantayhteys, migraatiot |
| Expenses router | `app/routers/expenses.py` | Kulujen CRUD + kuittien käsittely |
| Cost centers router | `app/routers/cost_centers.py` | Kustannuspaikkojen CRUD |
| Categories router | `app/routers/categories.py` | Kategorioiden CRUD |
| Reports router | `app/routers/reports.py` | Raportin laskenta ja näyttö |

---

## 2. Tietokannon rakenne

### 2.1 Entity-Relationship Diagram (ERD)

```
┌────────────────────┐
│  cost_centers      │
├────────────────────┤
│ id (PK)            │
│ name               │
│ center_type        │
│ vat_deductible     │
└────────┬───────────┘
         │ 1:N
         │
    ┌────┴────┐
    │          │
    ▼          ▼
┌──────────┐ ┌──────────────────┐
│expenses  │ │apartment_         │
├──────────┤ │year_settings      │
│id (PK)   │ ├──────────────────┤
│cost_center_id (FK)│id (PK)     │
│date      │ │cost_center_id(FK)│
│reference │ │year              │
│receipt   │ │maintenance_charge│
└──────┬───┘ └──────────────────┘
       │ 1:N
       ▼
┌──────────────────┐
│ expense_lines    │
├──────────────────┤
│ id (PK)          │
│ expense_id (FK)  │
│ category_id (FK) │──┐
│ description      │  │
│ gross_amount     │  │
│ vat_rate         │  │
│ vat_amount       │  │
│ net_amount       │  │
│ sort_order       │  │
└──────────────────┘  │
                      │
                  ┌───┴──────────────┐
                  │                  │
            ┌─────▼──────────────┐   │
            │expense_categories  │   │
            ├─────────────────────┤   │
            │id (PK)              │   │
            │name                 │◄──┤
            │category_type        │   │
            │UNIQUE(name, type)   │   │
            └─────────────────────┘   │
```

### 2.2 Taulujen kuvaukset

#### `cost_centers`
- Pääavain: `id`
- Sisältää asunnot, metsät, muut paikat
- `center_type` rajoitettu valinnaisiin arvoihin
- Kaikki `expenses` ja `apartment_year_settings` viittaa tähän

#### `expense_categories`
- Pääavain: `id`
- Komposiitti-uniikilta: `(name, category_type)`
- Sallii saman nimen eri tyypeille (esim. "Siivous" expense ja income)
- Käytetään `expense_lines`:ssä

#### `expenses`
- Pääavain: `id`
- Ulkoavain: `cost_center_id` → cost_centers (ON DELETE CASCADE)
- `reference`: Ainutlaatuinen, muodossa YYYY-NNN
- `receipt_image_path`: Tiedoston nimi (UUID + laajennus)
- 1:N suhde `expense_lines`:iin

#### `expense_lines`
- Pääavain: `id`
- Ulkoavain: `expense_id` → expenses (ON DELETE CASCADE)
This document explains the internal structure and design decisions of the Accounting Application (Kirjanpito-ohjelma).
- `sort_order` määrää rivin järjestyksen
## 1. Application Architecture

### 1.1 Layered Architecture
#### `apartment_year_settings`
- Pääavain: `id`
| Module | File | Responsibility |
- Vuoden asetukset hoitovastikkeelle jne.
| Main app | `app/main.py` | FastAPI application, middleware, startup |

| Models | `app/models.py` | SQLAlchemy models (ORM) |
---
| Database | `app/database.py` | Database connection, migrations |

| Expenses router | `app/routers/expenses.py` | Expenses CRUD + receipt handling |
## 3. Sovelluksen flow
| Cost centers router | `app/routers/cost_centers.py` | Cost centers CRUD |

| Categories router | `app/routers/categories.py` | Categories CRUD |
### 3.1 Kulun luonti
| Reports router | `app/routers/reports.py` | Report calculation and display |
```
## 2. Database Structure
User fills form in /expenses/new
### 2.1 Entity-Relationship Diagram (ERD)
          ↓
#### `cost_centers`
- Primary key: `id`
-- Contains apartments, forests, and other properties
-- `type` (note: NOT `center_type`) restricted to allowed values
-- All `expenses` and `apartment_year_settings` reference this table
_generate_reference() - Get unique YYYY-NNN
#### `expense_categories`
- Primary key: `id`
-- Composite unique constraint: `(name, category_type)`
-- Allows same name for different types (e.g., "Siivous" for both expense and income)
-- Used in `expense_lines`
          ↓
#### `expenses`
- Primary key: `id`
-- Foreign key: `cost_center_id` → cost_centers (ON DELETE CASCADE)
-- `reference`: Unique field in format YYYY-NNN
-- `receipt_image_path`: Filename (UUID + extension)
-- 1:N relationship with `expense_lines`
### 3.2 Raportin generointiprosessi
#### `expense_lines`
- Primary key: `id`
-- Foreign key: `expense_id` → expenses (ON DELETE CASCADE)
-- Foreign key: `category_id` → expense_categories (nullable)
-- Contains gross/net/VAT values
-- `sort_order` determines display order within transaction
          ↓
#### `apartment_year_settings`
- Primary key: `id`
-- Foreign key: `cost_center_id` → cost_centers
-- Annual settings for maintenance charges, etc.
_group_by_category() - Create grouped dict
## 3. Application Flow
          ↓
### 3.1 Expense Creation
Render yearly.html with collapsible rows
### 3.2 Report Generation Process
User clicks + to expand/collapse
## 4. Design Principles
          ↓
### 4.1 Multiple Lines per Transaction
JavaScript: toggleDetails() on client
**Rationale:** A cleaning service invoice might have laundry (24% VAT) + maintenance service (0% VAT) on the same bill.
```
**Implementation:** The `expense_lines` table contains all lines; `expenses` is just the "header" record.

**Benefit:** Flexible VAT calculation, easy categorization per line.
---
### 4.2 Reference Numbering (YYYY-NNN)

**Rationale:** Common practice in Finnish accounting systems.
## 4. Designin perusperiaatteet
**Implementation:** `_generate_reference()` parses existing references and finds the next available number.

**Benefit:** Prevents duplicates with uniqueness checking + incrementing.
### 4.1 Monta riviä per tapahtuma
### 4.3 Composite UNIQUE(name, category_type)

**Rationale:** The same category name can be both expense and income (e.g., "Siivous"/"Cleaning").
**Rationale:** Siivouspalvelussa voi olla pyykinpesu (24% ALV) + huoltopalvelu (0% ALV) samassa laskussa.
**Implementation:** Database constraint `UNIQUE(name, category_type)`.

**Benefit:** UI can display the same name in both category lists.
**Toteutus:** `expense_lines` taulu sisältää kaikki rivit. `expenses` on vain "otsikkoväline".
### 4.4 Collapsible Categories in Reports

**Rationale:** Many categories make reports long and hard to read.
**Etu:** Joustava ALV-laskenta, helppo kategorisointi per rivi.
**Implementation:** JavaScript `toggleDetails()` shows/hides detail rows below each category row.

**Benefit:** Compact view with all data accessible.
### 4.2 Viite-numerointi (YYYY-NNN)
### 4.5 PDF Optimization via Separate Script

**Rationale:** Receipt optimization is not part of the main application; it's a utility tool.
**Rationale:** Suomalaisissa laskulaskulmissa on yleinen käytäntö.
**Implementation:** Separate `split_pdf.py` script using PyMuPDF.

**Benefit:** Keeps main application simple, enables CLI usage.

## 5. Data Flow – Details
**Etu:** Estää duplikaatit tarkistuksella + inkrementaatiolla.
### 5.1 Expense Saving

### 5.2 Report Viewing

## 6. Performance Considerations
**Rationale:** Sama kategoria voi olla sekä kulu että tulo (esim. "Siivous").
### 6.1 Indexing

Recommended indexes:
**Toteutus:** Tietokannassa `UNIQUE(name, category_type)` rajoite.
### 6.2 Query Optimization
-- `_build_summary()`: One GROUP BY query per type
-- `_group_by_category()`: Loop with prefetch (sqlalchemy `joinedload`)
-- Cache reports if needed: `@cache(minutes=60)`

## 7. Security Considerations
**Rationale:** Monet kategoriat tekevät raportin pitkäksi ja vaikeaselkoiseksi.
### 7.1 File Upload

### 7.2 SQL Injection
**Toteutus:** JavaScript `toggleDetails()` näyttää/piilottaa rivin alle sijoitetut detail-rivit.
SQLAlchemy ORM protects against SQL injection using prepared statements.

### 7.3 CSRF
-- GET requests: No risk
-- POST/PUT/DELETE: No CSRF token (LAN application, no authentication)

## 8. Migrations
**Rationale:** Kuittien optimointi ei kuulu pääsovellukselle, vaan on utils-työkalu.
### 8.1 `_migrate_to_expense_lines`

Converts old single-amount schema to multi-line schema.
**Toteutus:** Erillinen `split_pdf.py` joka käyttää PyMuPDF:ää.
### 8.2 `_migrate_category_uniqueness`

Converts `UNIQUE(name)` → `UNIQUE(name, category_type)`.

## 9. Frontend Architecture
---
### 9.1 Template Structure

base.html (layout, nav)

├── expenses/list.html (loop expenses)
### 5.1 Kulun tallentaminen
├── expenses/form.html (multi-line form)

├── categories/list.html
```python
├── reports/index.html (report selection)
# expenses.py - POST /expenses/new
└── reports/yearly.html (collapsible summary)

# 1. Parse form data
### 9.2 JavaScript
cost_center_id = form['cost_center_id']
Primarily handles:
-- Real-time VAT calculation updates (`updateTotals()`)
-- Adding/removing lines (`addLine()`, `removeLine()`)
-- Category expansion (`toggleDetails()`)
reference = _generate_reference(db, year)
## 10. Test Plan

### 10.1 Unit Tests
# 3. Save receipt file
### 10.2 Integration Tests

## 11. Deployment
# 4. Create Expense record
### 11.1 Production Server
expense = Expense(
# Use gunicorn + systemd
    date=date,
    reference=reference,
    receipt_image_path=receipt_filename,
### 11.2 Database Backups
    entry_type="expense"
# Daily backup
db.add(expense)
db.flush()  # Get expense.id

### 11.3 SSL/TLS
# 5. Create ExpenseLines for each line in form
# nginx config
    vat_amount, net_amount = _compute_vat(line['gross'], line['vat_rate'])
    line_obj = ExpenseLine(
        expense_id=expense.id,
        category_id=line['category_id'],
        description=line['description'],
        gross_amount=line['gross'],
        vat_rate=line['vat_rate'],
**Last Updated:** April 26, 2026
    )
    db.add(line_obj)

db.commit()
```

### 5.2 Raportin katsominen

```python
# reports.py - GET /reports/yearly?cost_center_id=1&year=2026

# 1. Fetch all expenses for the center+year
expenses = db.query(Expense)\
    .join(ExpenseCategory)\
    .filter(
        Expense.cost_center_id == cost_center_id,
        YEAR(Expense.date) == year
    )\
    .all()

# 2. Build summary (aggregate by category)
summary = _build_summary(expenses)
# Returns: {income_rows: [...], expense_rows: [...], result_gross: ...}

# 3. Group by category for details
grouped = _group_by_category(expenses)
# Returns: {income: [{category: str, items: [(Expense, Line), ...]}], ...}

# 4. Render template
return templates.TemplateResponse("reports/yearly.html", {
    "center": center,
    "year": year,
    "summary": summary,
    "grouped": grouped
})
```

---

## 6. Suorituskykyharkintaa

### 6.1 Indeksointi

Suositeltavat indeksit:

```sql
CREATE INDEX idx_expenses_cost_center_id ON expenses(cost_center_id);
CREATE INDEX idx_expenses_date ON expenses(date);
CREATE INDEX idx_expense_lines_expense_id ON expense_lines(expense_id);
CREATE INDEX idx_expense_lines_category_id ON expense_lines(category_id);
```

### 6.2 Kyselyjen optimointi

- `_build_summary()`: Yksi GROUP BY -kysely per tyyppi
- `_group_by_category()`: Loop with prefetch (sqlalchemy `joinedload`)
- Raportit cachea tarvittaessa: `@cache(minutes=60)`

---

## 7. Turvallisuushuomiot

### 7.1 Tiedoston lataus

```python
def _save_receipt(file):
    # Validoi laajennus
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    
    # Luo UUID-nimi (estää path traversal)
    filename = f"{uuid.uuid4()}{ext}"
    
    # Tallenna receipts/ kansioon (ei web-accessible)
    filepath = os.path.join(RECEIPTS_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(file.file.read())
    
    return filename
```

### 7.2 SQL Injection

SQLAlchemy ORM suojaa SQL injectionilta käyttämällä prepared statements.

### 7.3 CSRF

- GET-pyynnöt: Ei riskiä
- POST/PUT/DELETE: Ei CSRF-tokenia (LAN-sovellus, ei autentikointia)

---

## 8. Migraatiot

### 8.1 `_migrate_to_expense_lines`

Muuntaa vanhan single-amount-skeeman multi-line-skeemaksi.

```python
def _migrate_to_expense_lines(db):
    """
    Vanha schema:
        expenses: amount, vat_rate, vat_amount, net_amount, category_id
    
    Uusi schema:
        expenses: (ei summia)
        expense_lines: (kaikki summat + category_id)
    """
    # 1. Tarkista onko migraatio jo tehty
    if db.query(ExpenseLine).first():
        return  # Already migrated
    
    # 2. Luo expense_lines-rivit vanhoista expenses-sarakkista
    for expense in db.query(Expense).all():
        line = ExpenseLine(
            expense_id=expense.id,
            category_id=expense.category_id,
            gross_amount=expense.amount,
            vat_rate=expense.vat_rate,
            vat_amount=expense.vat_amount,
            net_amount=expense.net_amount
        )
        db.add(line)
    
    db.commit()
```

### 8.2 `_migrate_category_uniqueness`

Muuntaa `UNIQUE(name)` → `UNIQUE(name, category_type)`.

---

## 9. Frontend-arkkitehtuuri

### 9.1 Template-haku

```
base.html (layout, nav)
├── expenses/list.html (loop expenses)
├── expenses/form.html (multi-line form)
├── categories/list.html
├── reports/index.html (report selection)
└── reports/yearly.html (collapsible summary)
```

### 9.2 JavaScript

Pääasiassa vain:
- ALV-laskennan real-time päivitys (`updateTotals()`)
- Rivin lisäys/poisto (`addLine()`, `removeLine()`)
- Kategorian laajeneminen (`toggleDetails()`)

---

## 10. Testisuunnitelma

### 10.1 Yksikkötestit (unit tests)

```python
# tests/test_models.py
def test_expense_total_gross():
    line1 = ExpenseLine(..., gross_amount=100, vat_rate=24)
    line2 = ExpenseLine(..., gross_amount=50, vat_rate=0)
    expense = Expense(lines=[line1, line2])
    
    assert expense.total_gross == 150
    assert expense.total_net == 130.65
    assert expense.total_vat == 19.35

# tests/test_compute_vat.py
def test_compute_vat_24pct():
    vat, net = _compute_vat(Decimal("100"), Decimal("24"))
    assert vat == Decimal("19.35")
    assert net == Decimal("80.65")
```

### 10.2 Integraatiotestit

```python
# tests/test_expenses_api.py
def test_create_expense_multiline():
    response = client.post("/expenses/new", data={
        "cost_center_id": "1",
        "date": "2026-04-26",
        "entry_type": "expense",
        "line_category_id[]": ["1", "2"],
        "line_description[]": ["Pyykinpesu", "Muu"],
        "line_gross_amount[]": ["100", "50"],
        "line_vat_rate[]": ["24", "0"]
    })
    
    assert response.status_code == 303
    
    expense = db.query(Expense).first()
    assert len(expense.lines) == 2
    assert expense.total_gross == 150
```

---

## 11. Deployment

### 11.1 Production-palvelin

```bash
# Käytä gunicorn + systemd

gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### 11.2 Tietokanta-varmuuskopiot

```bash
# Daily backup
0 2 * * * cp /app/accounting.db /backups/accounting.db.$(date +%s)
```

### 11.3 SSL/TLS

```nginx
# nginx config
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/cert.pem;
    
    proxy_pass http://127.0.0.1:8000;
}
```

---

**Päivityspäivä:** 2026-04-26
