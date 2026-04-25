import csv
import io
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostCenter, Expense, ExpenseCategory

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="templates")


def _build_summary(expenses: list[Expense]) -> dict:
    """Build per-category summary rows plus totals."""
    rows: dict[str, dict] = {}
    for exp in expenses:
        cat_name = exp.category.name if exp.category else "Luokittelematon"
        if cat_name not in rows:
            rows[cat_name] = {"category": cat_name, "count": 0, "net": Decimal("0"), "vat": Decimal("0"), "gross": Decimal("0")}
        rows[cat_name]["count"] += 1
        rows[cat_name]["net"] += exp.net_amount
        rows[cat_name]["vat"] += exp.vat_amount
        rows[cat_name]["gross"] += exp.gross_amount

    sorted_rows = sorted(rows.values(), key=lambda r: r["category"])
    totals = {
        "count": sum(r["count"] for r in sorted_rows),
        "net": sum(r["net"] for r in sorted_rows),
        "vat": sum(r["vat"] for r in sorted_rows),
        "gross": sum(r["gross"] for r in sorted_rows),
    }
    return {"rows": sorted_rows, "totals": totals}


@router.get("/", response_class=HTMLResponse)
def report_index(request: Request, db: Session = Depends(get_db)):
    centers = db.query(CostCenter).order_by(CostCenter.name).all()
    years = list(range(date.today().year, date.today().year - 6, -1))
    return templates.TemplateResponse(
        "reports/index.html",
        {"request": request, "centers": centers, "years": years, "current_year": date.today().year},
    )


@router.get("/yearly", response_class=HTMLResponse)
def yearly_report(
    request: Request,
    cost_center_id: int,
    year: int,
    db: Session = Depends(get_db),
):
    center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    if not center:
        return HTMLResponse("Kustannuspaikka ei löydy", status_code=404)

    expenses = (
        db.query(Expense)
        .filter(
            Expense.cost_center_id == cost_center_id,
            Expense.date >= date(year, 1, 1),
            Expense.date <= date(year, 12, 31),
        )
        .order_by(Expense.date)
        .all()
    )

    summary = _build_summary(expenses)
    centers = db.query(CostCenter).order_by(CostCenter.name).all()
    years = list(range(date.today().year, date.today().year - 6, -1))

    return templates.TemplateResponse(
        "reports/yearly.html",
        {
            "request": request,
            "center": center,
            "year": year,
            "expenses": expenses,
            "summary": summary,
            "centers": centers,
            "years": years,
        },
    )


@router.get("/yearly/csv")
def yearly_report_csv(
    cost_center_id: int,
    year: int,
    db: Session = Depends(get_db),
):
    center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    if not center:
        return HTMLResponse("Kustannuspaikka ei löydy", status_code=404)

    expenses = (
        db.query(Expense)
        .filter(
            Expense.cost_center_id == cost_center_id,
            Expense.date >= date(year, 1, 1),
            Expense.date <= date(year, 12, 31),
        )
        .order_by(Expense.date)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Päivämäärä", "Kuvaus", "Kategoria", "ALV %", "Netto (€)", "ALV (€)", "Brutto (€)", "Muistiinpanot"])
    for exp in expenses:
        cat_name = exp.category.name if exp.category else ""
        writer.writerow([
            exp.date.isoformat(),
            exp.description,
            cat_name,
            str(exp.vat_rate),
            str(exp.net_amount).replace(".", ","),
            str(exp.vat_amount).replace(".", ","),
            str(exp.gross_amount).replace(".", ","),
            exp.notes or "",
        ])

    # Totals row
    summary = _build_summary(expenses)
    t = summary["totals"]
    writer.writerow([])
    writer.writerow(["YHTEENSÄ", "", "", "",
                     str(t["net"]).replace(".", ","),
                     str(t["vat"]).replace(".", ","),
                     str(t["gross"]).replace(".", ",")])

    output.seek(0)
    filename = f"kulut_{center.name.replace(' ', '_')}_{year}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
