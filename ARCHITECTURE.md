# Architecture

## Layered Structure

```mermaid
flowchart TD
    Browser["Browser\nHTML + Bootstrap + app.js"]
    FastAPI["FastAPI\napp/main.py · routers/"]
    ORM["SQLAlchemy ORM\napp/models.py"]
    DB["SQLite\naccounting*.db"]

    Browser -- "HTTP (Jinja2 templates)" --> FastAPI
    FastAPI --> ORM
    ORM --> DB
```

## Database Schema (ERD)

```mermaid
erDiagram
    cost_centers {
        int id PK
        string name
        string type
        bool vat_deductible
        bool active
    }
    expenses {
        int id PK
        int cost_center_id FK
        string reference
        string entry_type
        date date
        string description
        string receipt_image_path
        bool no_receipt
    }
    expense_lines {
        int id PK
        int expense_id FK
        int category_id FK
        string description
        decimal gross_amount
        decimal vat_rate
        decimal net_amount
        decimal mileage_km
        decimal mileage_rate
        date line_date
        string vehicle
        string route_from
        string route_to
        int sort_order
    }
    expense_categories {
        int id PK
        string name
        string category_type
    }
    apartment_year_settings {
        int id PK
        int cost_center_id FK
        int year
        bool paaomavastike_tuloutettu
    }
    mileage_year_rates {
        int year PK
        decimal rate_eur_per_km
    }

    cost_centers ||--o{ expenses : ""
    cost_centers ||--o{ apartment_year_settings : ""
    expenses ||--|{ expense_lines : ""
    expense_lines }o--o| expense_categories : ""
```

## Expense Save Flow

```mermaid
sequenceDiagram
    actor User
    participant Form
    participant Router as expenses.py
    participant DB

    User->>Form: Fill in form
    Form->>Router: POST /expenses/new
    Router->>Router: _parse_lines() – km×rate or gross+VAT
    Router->>Router: _generate_reference() – YYYY-NNN
    Router->>Router: _save_receipt() – UUID filename
    Router->>DB: INSERT expenses + expense_lines
    Router-->>User: Redirect /expenses/
```

## Report Generation Flow

```mermaid
sequenceDiagram
    actor User
    participant Router as reports.py
    participant DB
    participant Template as yearly.html

    User->>Router: GET /reports/yearly?cost_center_id&year
    Router->>DB: Query expenses + lines (year + cost center)
    Router->>Router: _build_summary() – by category
    Router->>Router: _group_by_category() – detail rows
    Router->>DB: Query mileage_lines
    Router->>DB: Query mileage_year_rates
    Router-->>Template: Render summary + driving log
    Template-->>User: HTML (collapse via Bootstrap + JS)
```

## Module Structure

```mermaid
graph LR
    main["app/main.py\nlifespan, seed, middleware"]
    models["app/models.py\nORM models"]
    db["app/database.py\nengine, session, migrations"]
    expenses["routers/expenses.py\nexpenses + mileage"]
    reports["routers/reports.py\nyearly report + driving log"]
    categories["routers/categories.py"]
    cost_centers["routers/cost_centers.py"]
    receipt_paths["app/receipt_paths.py\nper-profile receipt directories"]

    main --> models
    main --> db
    main --> expenses
    main --> reports
    main --> categories
    main --> cost_centers
    expenses --> models
    expenses --> receipt_paths
    reports --> models
```

## Multi-Database Profile Support

```mermaid
flowchart LR
    ENV["Environment variable\nDB_PROFILE=ilkka"]
    resolve["database.py\n_default_db_path()"]
    file["data/accounting_ilkka.db"]
    receipts["data/receipts/accounting_ilkka/"]

    ENV --> resolve --> file
    resolve --> receipts
```

Start with a profile: `./start.sh --profile ilkka`
