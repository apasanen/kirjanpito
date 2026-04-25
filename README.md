# Accounting Application (Kirjanpito-ohjelma)

Finnish accounting application for managing expenses and income across multiple cost centers (apartments, forests, and other properties).

## Features

✅ Multi-line expenses and income  
✅ Receipt file management (PDF, images)  
✅ Automatic VAT calculation  
✅ Annual reports by category  
✅ Reference number system (YYYY-NNN)  
✅ PDF page splitting utility script  
✅ Collapsible categories in reports  

## Quick Start

### Windows

```bash
# Start test environment
start-test-env.bat
```

Open in browser: `http://127.0.0.1:8000`

### Linux / macOS

```bash
# Make script executable
chmod +x start-test-env.sh

# Start
./start-test-env.sh
```

Open in browser: `http://127.0.0.1:8000`

### Docker

```bash
# Start Docker Compose
docker-compose up

# Open in browser
http://127.0.0.1:8000
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── database.py          # Database configuration
│   └── routers/
│       ├── expenses.py      # Expenses API
│       ├── cost_centers.py  # Cost centers API
│       ├── categories.py    # Categories API
│       └── reports.py       # Reports API
├── templates/               # HTML templates (Jinja2)
├── static/                  # JavaScript, CSS
├── accounting.db            # SQLite database
├── receipts/                # Stored receipts
├── split_pdf.py             # PDF splitting utility
├── requirements.txt         # Python dependencies
├── SPECIFICATION.md         # Comprehensive technical documentation
└── start-test-env.*         # Startup scripts
```

## Technology

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend | FastAPI | 0.115.0 |
| Web Server | Uvicorn | 0.30.0 |
| ORM | SQLAlchemy | 2.0.49 |
| Database | SQLite | - |
| Frontend | Jinja2 + HTML + JS | 3.1.4 |
| PDF Processing | PyMuPDF | 1.24.0 |
| Image Processing | Pillow | 11.0.0 |

## Main Pages

| Page | URL | Description |
|------|-----|-------------|
| Expenses | `/expenses/` | List of transactions |
| New Transaction | `/expenses/new` | Form for new expense/income |
| Categories | `/categories/` | Category list |
| Annual Report | `/reports/yearly?cost_center_id=1&year=2026` | Comprehensive annual overview |

## Usage

### 1. Creating a New Transaction

1. Click **"New Transaction"**
2. Select:
   - Cost center
   - Date
   - Type (Expense / Income)
3. Add lines (category, description, gross amount, VAT %):
   - Click **"Add Line"**
4. Upload receipt (optional)
5. Click **"Save"**

### 2. Viewing a Report

1. Go to **"Reports"** → **"Annual Report"**
2. Select cost center and year
3. Click **+** next to category to view transactions
4. Click **−** to hide

### 3. PDF Splitting

Split multi-page PDFs into individual pages:

```bash
python split_pdf.py input.pdf output_dir --dpi 100 --quality 50
```

**Parameters:**
- `input.pdf` - Source file
- `output_dir` - Directory to save to (optional)
- `--dpi` - Resolution (36-300, default 85)
- `--quality` - JPEG quality (1-100, default 20)

## Database Migration

The database updates automatically on startup:

1. Conversion from single-line → multi-line transactions
2. Update of category UNIQUE constraints

Both are idempotent and safe.

## Development

### Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### Start Development Server

```bash
uvicorn app.main:app --reload
```

Server starts at `http://127.0.0.1:8000` and automatically reloads on changes.

### Code Validation

```bash
# Check syntax
python -m py_compile app/*.py

# Run tests (if available)
pytest tests/
```

## Documentation

See **[SPECIFICATION.md](SPECIFICATION.md)** for comprehensive technical documentation:
- Database schemas
- REST API documentation
- Frontend structure
- Migrations
- Test cases

## PDF Optimization

Split utility rasterizes PDFs as grayscale JPEG to save space:

```
Original:   56.23 MB (4-page PDF)
Optimized:  1.46 MB
Compression: 97.4%
```

**Parameters:**
- Default: DPI 85, quality 20 (smallest file)
- Medium: DPI 100, quality 40
- High: DPI 120, quality 60 (better quality)

## Troubleshooting

### Server Won't Start

```bash
# Check Python version (3.10+)
python --version

# Check database integrity
sqlite3 accounting.db ".tables"

# Try removing .venv and reinitializing
rmdir /s .venv  # Windows
rm -rf .venv    # Linux/macOS
```

### Dependency Issues

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Reinstall dependencies
pip install --no-cache-dir -r requirements.txt
```

## Security Measures

- **File validation:** Extension checked and named with UUID
- **SQL injection:** Protected by SQLAlchemy ORM
- **Receipts:** Stored in `receipts/` directory, not web-accessible

## Future Enhancements

- 👤 User account management
- 🌐 Multi-user support
- ☁️ Cloud integration (Google Drive, OneDrive)
- 📱 Mobile application
- 🌍 Localization (EN, SV, RU)
- 📊 Integration with accounting software

## License

Private use. All rights reserved.

## Author

**Antti**  
Created: April 26, 2026  
Updated: April 26, 2026

---

💡 **Need Help?** See [SPECIFICATION.md](SPECIFICATION.md) for technical details or open an issue.
