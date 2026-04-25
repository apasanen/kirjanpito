import os
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostCenter, Expense, ExpenseCategory, ExpenseLine
from app.receipt_paths import build_receipt_relative_path, get_receipts_dir_for_year, get_receipts_root

router = APIRouter(prefix="/expenses", tags=["expenses"])
templates = Jinja2Templates(directory="templates")

RECEIPTS_DIR = str(get_receipts_root())
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}


def _generate_reference(db: Session, year: int) -> str:
    # Build next reference from existing valid values (YYYY-NNN), not row count.
    pattern = re.compile(rf"^{year}-(\d{{3}})$")
    refs = db.query(Expense.reference).filter(
        Expense.reference.isnot(None),
        Expense.reference.like(f"{year}-%"),
    ).all()

    max_seq = 0
    for (ref,) in refs:
        if not ref:
            continue
        match = pattern.match(ref)
        if match:
            max_seq = max(max_seq, int(match.group(1)))

    next_seq = max_seq + 1
    while True:
        candidate = f"{year}-{next_seq:03d}"
        exists = db.query(Expense.id).filter(Expense.reference == candidate).first()
        if not exists:
            return candidate
        next_seq += 1


def _save_receipt(file, expense_year: int) -> Optional[str]:
    if not file or not getattr(file, "filename", None):
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    content = file.file.read()
    if not content:
        return None

    # Save original file without optimization
    filename = f"{uuid.uuid4()}{ext}"
    target_dir = get_receipts_dir_for_year(expense_year)
    with open(target_dir / filename, "wb") as f:
        f.write(content)
    return build_receipt_relative_path(filename, expense_year)





def _compute_vat(gross: Decimal, vat_rate: Decimal):
    if vat_rate <= 0:
        return Decimal("0.00"), gross.quantize(Decimal("0.01"))
    vat_amount = (gross * vat_rate / (100 + vat_rate)).quantize(Decimal("0.01"))
    return vat_amount, (gross - vat_amount).quantize(Decimal("0.01"))


def _lines_to_dicts(lines) -> list:
    return [
        {
            "category_id": l.category_id,
            "description": l.description or "",
            "gross_amount": str(l.gross_amount),
            "vat_rate": str(l.vat_rate),
        }
        for l in lines
    ]


def _empty_line() -> dict:
    return {"category_id": None, "description": "", "gross_amount": "", "vat_rate": "0"}


def _parse_lines(form) -> list:
    categories = form.getlist("line_category_id")
    descriptions = form.getlist("line_description")
    gross_amounts = form.getlist("line_gross_amount")
    vat_rates = form.getlist("line_vat_rate")
    result = []
    for i, (cat_id, desc, gross_str, vat_str) in enumerate(
        zip(categories, descriptions, gross_amounts, vat_rates)
    ):
        try:
            gross = Decimal((gross_str or "0").replace(",", "."))
        except (InvalidOperation, ValueError):
            continue
        if gross <= 0:
            continue
        try:
            rate = Decimal((vat_str or "0").replace(",", "."))
        except (InvalidOperation, ValueError):
            rate = Decimal("0")
        vat_amount, net_amount = _compute_vat(gross, rate)
        result.append({
            "category_id": int(cat_id) if cat_id else None,
            "description": (desc or "").strip(),
            "gross_amount": gross,
            "vat_rate": rate,
            "vat_amount": vat_amount,
            "net_amount": net_amount,
            "sort_order": i,
        })
    return result


@router.get("/", response_class=HTMLResponse)
def list_expenses(
    request: Request,
    cost_center_id: Optional[str] = None,
    year: Optional[str] = None,
    entry_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    cost_center_id = int(cost_center_id) if cost_center_id else None
    year = int(year) if year else None
    query = db.query(Expense)
    if cost_center_id:
        query = query.filter(Expense.cost_center_id == cost_center_id)
    if year:
        query = query.filter(Expense.date >= date(year, 1, 1), Expense.date <= date(year, 12, 31))
    if entry_type in ("expense", "income"):
        query = query.filter(Expense.entry_type == entry_type)
    expenses = query.order_by(Expense.date.desc()).all()
    centers = db.query(CostCenter).filter(CostCenter.active == True).order_by(CostCenter.name).all()
    years = list(range(date.today().year, date.today().year - 6, -1))
    return templates.TemplateResponse(
        request,
        "expenses/list.html",
        {
            "request": request,
            "expenses": expenses,
            "centers": centers,
            "selected_center": cost_center_id,
            "selected_year": year,
            "selected_type": entry_type,
            "years": years,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_expense_form(
    request: Request,
    type: Optional[str] = None,
    copy_from: Optional[int] = None,
    db: Session = Depends(get_db),
):
    centers = db.query(CostCenter).filter(CostCenter.active == True).order_by(CostCenter.name).all()
    prefill = None
    if copy_from:
        source = db.query(Expense).filter(Expense.id == copy_from).first()
        if source:
            prefill = source
            preset_type = source.entry_type
        else:
            preset_type = type if type in ("expense", "income") else "expense"
    else:
        preset_type = type if type in ("expense", "income") else "expense"

    categories = db.query(ExpenseCategory).filter(
        ExpenseCategory.category_type == preset_type
    ).order_by(ExpenseCategory.name).all()
    form_lines = _lines_to_dicts(prefill.lines) if prefill else [_empty_line()]

    return templates.TemplateResponse(
        request,
        "expenses/form.html",
        {
            "request": request,
            "expense": None,
            "prefill": prefill,
            "form_lines": form_lines,
            "centers": centers,
            "categories": categories,
            "today": date.today().isoformat(),
            "preset_type": preset_type,
        },
    )


@router.post("/new")
async def create_expense(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    entry_type = form.get("entry_type", "expense")
    if entry_type not in ("expense", "income"):
        entry_type = "expense"
    try:
        cost_center_id = int(form.get("cost_center_id", 0))
        exp_date = date.fromisoformat(form.get("expense_date", ""))
    except (ValueError, TypeError):
        return RedirectResponse("/expenses/new", status_code=303)

    description = (form.get("description") or "").strip()
    notes = (form.get("notes") or "").strip() or None
    receipt_filename = _save_receipt(form.get("receipt"), exp_date.year)
    lines = _parse_lines(form)
    if not lines:
        return RedirectResponse(f"/expenses/new?type={entry_type}", status_code=303)

    reference = _generate_reference(db, exp_date.year)
    expense = Expense(
        reference=reference,
        entry_type=entry_type,
        cost_center_id=cost_center_id,
        date=exp_date,
        description=description,
        notes=notes,
        receipt_image_path=receipt_filename,
    )
    db.add(expense)
    db.flush()
    for line_data in lines:
        db.add(ExpenseLine(expense_id=expense.id, **line_data))
    db.commit()
    return RedirectResponse("/expenses/", status_code=303)


@router.get("/{expense_id}/view", response_class=HTMLResponse)
def view_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)
    centers = db.query(CostCenter).filter(
        (CostCenter.active == True) | (CostCenter.id == expense.cost_center_id)
    ).order_by(CostCenter.name).all()
    categories = db.query(ExpenseCategory).filter(
        ExpenseCategory.category_type == expense.entry_type
    ).order_by(ExpenseCategory.name).all()
    form_lines = _lines_to_dicts(expense.lines) if expense.lines else [_empty_line()]
    return templates.TemplateResponse(
        request,
        "expenses/form.html",
        {
            "request": request,
            "expense": expense,
            "prefill": None,
            "form_lines": form_lines,
            "centers": centers,
            "categories": categories,
            "read_only": True,
        },
    )


@router.get("/{expense_id}/edit", response_class=HTMLResponse)
def edit_expense_form(expense_id: int, request: Request, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)
    centers = db.query(CostCenter).filter(
        (CostCenter.active == True) | (CostCenter.id == expense.cost_center_id)
    ).order_by(CostCenter.name).all()
    categories = db.query(ExpenseCategory).filter(
        ExpenseCategory.category_type == expense.entry_type
    ).order_by(ExpenseCategory.name).all()
    form_lines = _lines_to_dicts(expense.lines) if expense.lines else [_empty_line()]
    return templates.TemplateResponse(
        request,
        "expenses/form.html",
        {
            "request": request,
            "expense": expense,
            "prefill": None,
            "form_lines": form_lines,
            "centers": centers,
            "categories": categories,
        },
    )


@router.post("/{expense_id}/edit")
async def update_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)
    form = await request.form()
    try:
        expense.cost_center_id = int(form.get("cost_center_id", expense.cost_center_id))
        expense.date = date.fromisoformat(form.get("expense_date", str(expense.date)))
    except (ValueError, TypeError):
        return RedirectResponse(f"/expenses/{expense_id}/edit", status_code=303)

    expense.description = (form.get("description") or "").strip()
    expense.notes = (form.get("notes") or "").strip() or None

    receipt = form.get("receipt")
    if receipt and getattr(receipt, "filename", None):
        new_filename = _save_receipt(receipt, expense.date.year)
        if new_filename:
            if expense.receipt_image_path:
                old_path = Path(RECEIPTS_DIR) / expense.receipt_image_path
                if old_path.exists():
                    old_path.unlink()
            expense.receipt_image_path = new_filename

    lines = _parse_lines(form)
    if lines:
        for old in list(expense.lines):
            db.delete(old)
        db.flush()
        for line_data in lines:
            db.add(ExpenseLine(expense_id=expense.id, **line_data))
    db.commit()
    return RedirectResponse("/expenses/", status_code=303)


@router.post("/{expense_id}/delete")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        if expense.receipt_image_path:
            path = Path(RECEIPTS_DIR) / expense.receipt_image_path
            if path.exists():
                path.unlink()
        db.delete(expense)
        db.commit()
    return RedirectResponse("/expenses/", status_code=303)


