from pathlib import Path
import shutil
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.version import VERSION_INFO
from app.routers import cost_centers, expenses, reports, categories
from app.receipt_paths import build_receipt_relative_path, get_db_folder_name


def _backfill_references():
    """Assign reference numbers to existing expenses that don't have one yet."""
    from app.database import SessionLocal
    from app.models import Expense
    db = SessionLocal()
    try:
        missing = (
            db.query(Expense)
            .filter(Expense.reference.is_(None))
            .order_by(Expense.date, Expense.id)
            .all()
        )
        if not missing:
            return
        # Count already-assigned references per year so we continue from the right number
        from collections import defaultdict
        counters: dict[int, int] = defaultdict(int)
        for exp in db.query(Expense).filter(Expense.reference.isnot(None)).all():
            year = exp.date.year
            try:
                seq = int(exp.reference.split("-")[1])
                if seq > counters[year]:
                    counters[year] = seq
            except (IndexError, ValueError):
                pass
        for exp in missing:
            year = exp.date.year
            counters[year] += 1
            exp.reference = f"{year}-{counters[year]:03d}"
        db.commit()
    finally:
        db.close()


def _seed_default_categories():
    from app.database import SessionLocal
    from app.models import ExpenseCategory
    db = SessionLocal()
    try:
        expense_defaults = [
            "Hoitovastike",
            "Rahoitusvastike",
            "Remontit ja korjaukset",
            "Vakuutus",
            "Lainan korot",
            "Kiinteistövero",
            "Vuokrauskulut",
            "Tilitoimisto",
            "Metsänhoito",
            "Puunmyyntikulut",
            "Matkakulut",
            "Toimistokulut",
            "Muut kulut",
        ]
        income_defaults = [
            "Vuokratulo",
            "Puunmyyntitulo",
            "Muut tulot",
        ]
        existing_names = {c.name for c in db.query(ExpenseCategory).all()}
        for name in expense_defaults:
            if name not in existing_names:
                db.add(ExpenseCategory(name=name, category_type="expense"))
        for name in income_defaults:
            if name not in existing_names:
                db.add(ExpenseCategory(name=name, category_type="income"))
        db.commit()
    finally:
        db.close()


def _organize_receipts_by_db_and_year():
    """Move existing receipts to data/receipts/<db_name>/<year>/ and update DB paths."""
    from app.database import SessionLocal
    from app.models import Expense

    db = SessionLocal()
    receipts_root = Path("data") / "receipts"
    receipts_root.mkdir(parents=True, exist_ok=True)
    changed = False

    try:
        expenses_with_receipts = db.query(Expense).filter(Expense.receipt_image_path.isnot(None)).all()
        for exp in expenses_with_receipts:
            current_rel = (exp.receipt_image_path or "").replace("\\", "/").strip("/")
            if not current_rel:
                continue

            filename = Path(current_rel).name
            target_rel = build_receipt_relative_path(filename, exp.date.year)
            if current_rel == target_rel:
                continue

            source = receipts_root / current_rel
            target = receipts_root / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)

            if source.exists() and source.resolve() != target.resolve():
                if target.exists():
                    stem = target.stem
                    suffix = target.suffix
                    i = 1
                    while True:
                        candidate = target.with_name(f"{stem}_{i}{suffix}")
                        if not candidate.exists():
                            target = candidate
                            target_rel = f"{get_db_folder_name()}/{exp.date.year}/{target.name}"
                            break
                        i += 1
                shutil.move(str(source), str(target))

            if target.exists():
                exp.receipt_image_path = target_rel
                changed = True

        if changed:
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_default_categories()
    _backfill_references()
    _organize_receipts_by_db_and_year()
    yield


app = FastAPI(title="Kirjanpito", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
Path("data/receipts").mkdir(parents=True, exist_ok=True)
app.mount("/receipts", StaticFiles(directory="data/receipts"), name="receipts")

app.include_router(cost_centers.router)
app.include_router(expenses.router)
app.include_router(reports.router)
app.include_router(categories.router)


@app.get("/api/version")
def get_version():
    """Get application version and commit info."""
    return VERSION_INFO


@app.middleware("http")
async def add_version_to_context(request, call_next):
    """Make version available to all template responses."""
    request.state.version = VERSION_INFO
    response = await call_next(request)
    return response


@app.get("/")
def root():
    return RedirectResponse("/expenses/")
