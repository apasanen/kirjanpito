import yaml
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import cost_centers, expenses, reports

YAML_PATH = Path("cost_centers.yaml")


def _sync_cost_centers_from_yaml():
    """Upsert cost centers from YAML file into the database."""
    if not YAML_PATH.exists():
        return
    from app.database import SessionLocal
    from app.models import CostCenter
    with YAML_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = (data or {}).get("cost_centers", [])
    db = SessionLocal()
    try:
        for entry in entries:
            cc_id = entry.get("id")
            if not cc_id:
                continue
            existing = db.query(CostCenter).filter(CostCenter.id == cc_id).first()
            if existing:
                existing.name = entry["name"]
                existing.type = entry.get("type", "other")
                existing.description = entry.get("description") or None
                existing.vat_deductible = bool(entry.get("vat_deductible", False))
            else:
                db.add(CostCenter(
                    id=cc_id,
                    name=entry["name"],
                    type=entry.get("type", "other"),
                    description=entry.get("description") or None,
                    vat_deductible=bool(entry.get("vat_deductible", False)),
                    active=True,
                ))
        db.commit()
    finally:
        db.close()


def _seed_default_categories():
    from app.database import SessionLocal
    from app.models import ExpenseCategory
    db = SessionLocal()
    try:
        if db.query(ExpenseCategory).count() == 0:
            defaults = [
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
            for name in defaults:
                db.add(ExpenseCategory(name=name))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _sync_cost_centers_from_yaml()
    _seed_default_categories()
    yield


app = FastAPI(title="Kirjanpito", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/receipts", StaticFiles(directory="receipts"), name="receipts")

app.include_router(cost_centers.router)
app.include_router(expenses.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return RedirectResponse("/expenses/")
