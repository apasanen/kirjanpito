import csv
import io
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import extract
from sqlalchemy.orm import Session
import fitz

from app.database import get_db
from app.models import ApartmentYearSetting, CostCenter, Expense, ExpenseCategory, ExpenseLine, MileageYearRate
from app.receipt_paths import get_receipts_root

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="templates")


def _get_years_with_data(db: Session) -> list[int]:
    rows = (
        db.query(extract("year", Expense.date).label("year"))
        .distinct()
        .order_by(extract("year", Expense.date).desc())
        .all()
    )
    return [int(row.year) for row in rows if row.year is not None]


def _build_summary(expenses: list) -> dict:
    """Build per-category summary rows plus totals, split by entry_type."""
    income_rows: dict = {}
    expense_rows: dict = {}

    for exp in expenses:
        bucket = income_rows if exp.entry_type == "income" else expense_rows
        for line in exp.lines:
            cat_name = line.category.name if line.category else "Luokittelematon"
            if cat_name not in bucket:
                bucket[cat_name] = {"category": cat_name, "count": 0, "net": Decimal("0"), "vat": Decimal("0"), "gross": Decimal("0")}
            bucket[cat_name]["count"] += 1
            bucket[cat_name]["net"] += line.net_amount
            bucket[cat_name]["vat"] += line.vat_amount
            bucket[cat_name]["gross"] += line.gross_amount

    def _totals(rows):
        return {
            "count": sum(r["count"] for r in rows),
            "net": sum(r["net"] for r in rows),
            "vat": sum(r["vat"] for r in rows),
            "gross": sum(r["gross"] for r in rows),
        }

    inc_rows = sorted(income_rows.values(), key=lambda r: r["category"])
    exp_rows = sorted(expense_rows.values(), key=lambda r: r["category"])
    inc_totals = _totals(inc_rows)
    exp_totals = _totals(exp_rows)

    result_gross = inc_totals["gross"] - exp_totals["gross"]

    return {
        "income_rows": inc_rows,
        "income_totals": inc_totals,
        "expense_rows": exp_rows,
        "expense_totals": exp_totals,
        "result_gross": result_gross,
    }


def _group_by_category(expenses: list) -> dict:
    """Return lines grouped by entry_type then category, with per-group subtotals."""
    from collections import defaultdict

    def _make_group(exp_list):
        groups = defaultdict(list)
        for exp in exp_list:
            for line in exp.lines:
                key = line.category.name if line.category else "Luokittelematon"
                groups[key].append((exp, line))
        result = []
        for cat_name in sorted(groups.keys()):
            items = groups[cat_name]
            result.append({
                "category": cat_name,
                "items": items,  # list of (expense, line) tuples
                "subtotal_net": sum(l.net_amount for _, l in items),
                "subtotal_vat": sum(l.vat_amount for _, l in items),
                "subtotal_gross": sum(l.gross_amount for _, l in items),
            })
        return result

    income = [e for e in expenses if e.entry_type == "income"]
    expense = [e for e in expenses if e.entry_type != "income"]
    return {
        "income": _make_group(income),
        "expense": _make_group(expense),
    }


# Category name buckets for tax mapping
_TAX_HOITOVASTIKE = {"Hoitovastike", "Vesimaksu"}
_TAX_PAAOMAVASTIKE = {"Rahoitusvastike"}
_TAX_VUOSIKORJAUKSET = {"Remontit ja korjaukset"}


def _build_tax_section(expenses: list, paaomavastike_tuloutettu: bool) -> dict:
    """Build Finnish rental tax declaration figures."""
    income_gross = sum(
        (l.gross_amount for e in expenses if e.entry_type == "income" for l in e.lines), Decimal("0")
    )
    hoitovastike = sum(
        (l.gross_amount for e in expenses if e.entry_type != "income"
         for l in e.lines if l.category and l.category.name in _TAX_HOITOVASTIKE),
        Decimal("0"),
    )
    paaomavastike = sum(
        (l.gross_amount for e in expenses if e.entry_type != "income"
         for l in e.lines if l.category and l.category.name in _TAX_PAAOMAVASTIKE),
        Decimal("0"),
    )
    vuosikorjaukset = sum(
        (l.gross_amount for e in expenses if e.entry_type != "income"
         for l in e.lines if l.category and l.category.name in _TAX_VUOSIKORJAUKSET),
        Decimal("0"),
    )
    known = _TAX_HOITOVASTIKE | _TAX_PAAOMAVASTIKE | _TAX_VUOSIKORJAUKSET
    muut = sum(
        (l.gross_amount for e in expenses if e.entry_type != "income"
         for l in e.lines if not l.category or l.category.name not in known),
        Decimal("0"),
    )
    deductible_paaomavastike = paaomavastike if paaomavastike_tuloutettu else Decimal("0")
    total_deductions = hoitovastike + deductible_paaomavastike + vuosikorjaukset + muut
    verotettava_tulos = income_gross - total_deductions
    return {
        "income_gross": income_gross,
        "hoitovastike": hoitovastike,
        "paaomavastike": paaomavastike,
        "paaomavastike_tuloutettu": paaomavastike_tuloutettu,
        "deductible_paaomavastike": deductible_paaomavastike,
        "vuosikorjaukset": vuosikorjaukset,
        "muut": muut,
        "total_deductions": total_deductions,
        "verotettava_tulos": verotettava_tulos,
    }


@router.get("/", response_class=HTMLResponse)
def report_index(request: Request, db: Session = Depends(get_db)):
    centers = db.query(CostCenter).filter(CostCenter.active == True).order_by(CostCenter.name).all()
    years = _get_years_with_data(db)
    current_year = years[0] if years else None
    return templates.TemplateResponse(
        request,
        "reports/index.html",
        {"request": request, "centers": centers, "years": years, "current_year": current_year},
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
        .order_by(Expense.entry_type, Expense.date)
        .all()
    )

    summary = _build_summary(expenses)
    grouped = _group_by_category(expenses)
    missing_receipts = [
        exp for exp in expenses
        if exp.entry_type == "expense" and not exp.receipt_image_path and not exp.no_receipt
    ]
    centers = db.query(CostCenter).filter(CostCenter.active == True).order_by(CostCenter.name).all()
    years = _get_years_with_data(db)

    # Tax section only for apartment cost centers
    tax_section = None
    year_setting = None
    if center.type == "apartment":
        year_setting = db.query(ApartmentYearSetting).filter(
            ApartmentYearSetting.cost_center_id == cost_center_id,
            ApartmentYearSetting.year == year,
        ).first()
        tuloutettu = year_setting.paaomavastike_tuloutettu if year_setting else True
        tax_section = _build_tax_section(expenses, tuloutettu)

    return templates.TemplateResponse(
        request,
        "reports/yearly.html",
        {
            "request": request,
            "center": center,
            "year": year,
            "grouped": grouped,
            "summary": summary,
            "missing_receipts": missing_receipts,
            "centers": centers,
            "years": years,
            "tax_section": tax_section,
            "paaomavastike_tuloutettu": year_setting.paaomavastike_tuloutettu if year_setting else True,
        },
    )


@router.post("/yearly/set-paaomavastike")
def set_paaomavastike(
    cost_center_id: int = Form(...),
    year: int = Form(...),
    tuloutettu: str = Form("1"),
    db: Session = Depends(get_db),
):
    setting = db.query(ApartmentYearSetting).filter(
        ApartmentYearSetting.cost_center_id == cost_center_id,
        ApartmentYearSetting.year == year,
    ).first()
    if not setting:
        setting = ApartmentYearSetting(cost_center_id=cost_center_id, year=year)
        db.add(setting)
    setting.paaomavastike_tuloutettu = (tuloutettu == "1")
    db.commit()
    return RedirectResponse(f"/reports/yearly?cost_center_id={cost_center_id}&year={year}", status_code=303)


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
    writer.writerow(["Tunnus", "Päivämäärä", "Tyyppi", "Tositekuvaus", "Kategoria", "Rivin kuvaus", "ALV %", "Netto (€)", "ALV (€)", "Brutto (€)", "Muistiinpanot"])
    for exp in expenses:
        type_label = "Tulo" if exp.entry_type == "income" else "Kulu"
        for line in exp.lines:
            cat_name = line.category.name if line.category else ""
            writer.writerow([
                exp.reference or "",
                exp.date.isoformat(),
                type_label,
                exp.description or "",
                cat_name,
                line.description or "",
                str(line.vat_rate),
                str(line.net_amount).replace(".", ","),
                str(line.vat_amount).replace(".", ","),
                str(line.gross_amount).replace(".", ","),
                exp.notes or "",
            ])

    summary = _build_summary(expenses)
    t_inc = summary["income_totals"]
    t_exp = summary["expense_totals"]
    writer.writerow([])
    writer.writerow(["TULOT YHTEENSÄ", "", "", "", "",
                     str(t_inc["net"]).replace(".", ","),
                     str(t_inc["vat"]).replace(".", ","),
                     str(t_inc["gross"]).replace(".", ",")])
    writer.writerow(["KULUT YHTEENSÄ", "", "", "", "",
                     str(t_exp["net"]).replace(".", ","),
                     str(t_exp["vat"]).replace(".", ","),
                     str(t_exp["gross"]).replace(".", ",")])
    result = summary["result_gross"]
    writer.writerow(["TULOS", "", "", "", "", "", "",
                     str(result).replace(".", ",")])

    output.seek(0)
    filename = f"kulut_{center.name.replace(' ', '_')}_{year}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _get_mileage_rate(db: Session, year: int) -> Decimal:
    setting = db.get(MileageYearRate, year)
    return setting.rate_eur_per_km if setting else Decimal("0.57")


@router.post("/mileage/set-rate")
def set_mileage_rate(
    cost_center_id: int = Form(...),
    year: int = Form(...),
    rate_eur_per_km: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        rate = Decimal(rate_eur_per_km.replace(",", "."))
        if rate <= 0:
            raise ValueError
    except Exception:
        return RedirectResponse(f"/reports/mileage?cost_center_id={cost_center_id}&year={year}", status_code=303)
    setting = db.get(MileageYearRate, year)
    if not setting:
        setting = MileageYearRate(year=year, rate_eur_per_km=rate)
        db.add(setting)
    else:
        setting.rate_eur_per_km = rate
    db.commit()
    return RedirectResponse(f"/reports/mileage?cost_center_id={cost_center_id}&year={year}", status_code=303)


@router.get("/mileage", response_class=HTMLResponse)
def mileage_report(
    request: Request,
    cost_center_id: int,
    year: int,
    db: Session = Depends(get_db),
):
    center = db.query(CostCenter).filter(CostCenter.id == cost_center_id).first()
    if not center:
        return HTMLResponse("Kustannuspaikka ei löydy", status_code=404)

    mileage_lines = (
        db.query(ExpenseLine)
        .join(Expense, ExpenseLine.expense_id == Expense.id)
        .filter(
            Expense.cost_center_id == cost_center_id,
            Expense.date >= date(year, 1, 1),
            Expense.date <= date(year, 12, 31),
            ExpenseLine.mileage_km.isnot(None),
        )
        .order_by(Expense.date, Expense.id, ExpenseLine.sort_order)
        .all()
    )
    centers = db.query(CostCenter).filter(CostCenter.active == True).order_by(CostCenter.name).all()
    years = _get_years_with_data(db)
    total_km = sum((line.mileage_km or Decimal("0")) for line in mileage_lines)
    total_amount = sum((line.gross_amount for line in mileage_lines), Decimal("0"))
    mileage_rate = _get_mileage_rate(db, year)

    return templates.TemplateResponse(
        request,
        "reports/mileage.html",
        {
            "request": request,
            "center": center,
            "year": year,
            "mileage_lines": mileage_lines,
            "total_km": total_km,
            "total_amount": total_amount,
            "mileage_rate": mileage_rate,
            "centers": centers,
            "years": years,
        },
    )


def _stamp_reference(page: fitz.Page, reference_text: str):
    # Add visible receipt identifier to top-left corner of each page.
    label = f"Kuitin tunnus: {reference_text}"
    point = fitz.Point(24, 30)
    page.insert_text(
        point,
        label,
        fontsize=14,
        fontname="helv",
        color=(0.15, 0.15, 0.15),
    )


def _append_pdf_receipt(target_doc: fitz.Document, source_path: Path, reference_text: str):
    src = fitz.open(source_path)
    try:
        start_index = target_doc.page_count
        target_doc.insert_pdf(src)
        for i in range(start_index, target_doc.page_count):
            _stamp_reference(target_doc[i], reference_text)
    finally:
        src.close()


def _append_image_receipt(target_doc: fitz.Document, source_path: Path, reference_text: str):
    # Render image onto a single A4 portrait page and stamp with the receipt id.
    img_info = fitz.image_profile(str(source_path))
    width = img_info.get("width", 1200)
    height = img_info.get("height", 1600)

    page_width = fitz.paper_size("a4")[0]
    page_height = fitz.paper_size("a4")[1]
    page = target_doc.new_page(width=page_width, height=page_height)

    margin = 24
    top_reserved = 22
    content_rect = fitz.Rect(margin, margin + top_reserved, page_width - margin, page_height - margin)
    img_rect = fitz.Rect(0, 0, width, height)
    placed = img_rect.torect(content_rect)
    page.insert_image(placed, filename=str(source_path), keep_proportion=True)
    _stamp_reference(page, reference_text)


@router.get("/yearly/receipts-pdf")
def yearly_receipts_pdf(
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
            Expense.receipt_image_path.isnot(None),
        )
        .order_by(Expense.date, Expense.id)
        .all()
    )

    receipts_root = get_receipts_root()
    merged = fitz.open()
    appended_count = 0

    for exp in expenses:
        rel = (exp.receipt_image_path or "").replace("\\", "/").strip("/")
        if not rel:
            continue
        src = receipts_root / rel
        if not src.exists() or not src.is_file():
            continue

        reference_text = (exp.reference or f"ID-{exp.id}").strip()
        suffix = src.suffix.lower()
        try:
            if suffix == ".pdf":
                _append_pdf_receipt(merged, src, reference_text)
                appended_count += 1
            elif suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                _append_image_receipt(merged, src, reference_text)
                appended_count += 1
        except Exception:
            # Skip unreadable files and continue building the bundle.
            continue

    if appended_count == 0 or merged.page_count == 0:
        merged.close()
        return HTMLResponse("Valitulla rajauksella ei löytynyt tositteita PDF-lataukseen.", status_code=404)

    pdf_bytes = merged.tobytes(garbage=4, deflate=True)
    merged.close()

    safe_name = center.name.replace(" ", "_")
    filename = f"tositteet_{safe_name}_{year}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
