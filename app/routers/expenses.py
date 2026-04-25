import os
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostCenter, Expense, ExpenseCategory

router = APIRouter(prefix="/expenses", tags=["expenses"])
templates = Jinja2Templates(directory="templates")

RECEIPTS_DIR = "receipts"
os.makedirs(RECEIPTS_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}


def _save_receipt(file: UploadFile) -> Optional[str]:
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(RECEIPTS_DIR, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return filename


def _compute_vat(gross: Decimal, vat_rate: Decimal) -> tuple[Decimal, Decimal]:
    """Returns (vat_amount, net_amount) from gross and VAT rate %."""
    if vat_rate <= 0:
        return Decimal("0.00"), gross.quantize(Decimal("0.01"))
    vat_amount = (gross * vat_rate / (100 + vat_rate)).quantize(Decimal("0.01"))
    net_amount = (gross - vat_amount).quantize(Decimal("0.01"))
    return vat_amount, net_amount


@router.get("/", response_class=HTMLResponse)
def list_expenses(
    request: Request,
    cost_center_id: Optional[str] = None,
    year: Optional[str] = None,
    db: Session = Depends(get_db),
):
    cost_center_id = int(cost_center_id) if cost_center_id else None
    year = int(year) if year else None
    query = db.query(Expense)
    if cost_center_id:
        query = query.filter(Expense.cost_center_id == cost_center_id)
    if year:
        query = query.filter(Expense.date >= date(year, 1, 1), Expense.date <= date(year, 12, 31))
    expenses = query.order_by(Expense.date.desc()).all()
    centers = db.query(CostCenter).order_by(CostCenter.name).all()
    years = list(range(date.today().year, date.today().year - 6, -1))
    return templates.TemplateResponse(
        "expenses/list.html",
        {
            "request": request,
            "expenses": expenses,
            "centers": centers,
            "selected_center": cost_center_id,
            "selected_year": year,
            "years": years,
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_expense_form(request: Request, db: Session = Depends(get_db)):
    centers = db.query(CostCenter).filter(CostCenter.active == True).order_by(CostCenter.name).all()
    categories = db.query(ExpenseCategory).order_by(ExpenseCategory.name).all()
    return templates.TemplateResponse(
        "expenses/form.html",
        {
            "request": request,
            "expense": None,
            "centers": centers,
            "categories": categories,
            "today": date.today().isoformat(),
        },
    )


@router.post("/new")
async def create_expense(
    request: Request,
    cost_center_id: int = Form(...),
    category_id: str = Form(""),
    expense_date: str = Form(...),
    description: str = Form(...),
    gross_amount: str = Form(...),
    vat_rate: str = Form("25.5"),
    notes: str = Form(""),
    receipt: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    try:
        gross = Decimal(gross_amount.replace(",", "."))
        rate = Decimal(vat_rate.replace(",", "."))
    except InvalidOperation:
        return RedirectResponse("/expenses/new", status_code=303)

    vat_amount, net_amount = _compute_vat(gross, rate)
    receipt_filename = _save_receipt(receipt)

    expense = Expense(
        cost_center_id=cost_center_id,
        category_id=int(category_id) if category_id else None,
        date=date.fromisoformat(expense_date),
        description=description,
        gross_amount=gross,
        vat_rate=rate,
        vat_amount=vat_amount,
        net_amount=net_amount,
        receipt_image_path=receipt_filename,
        notes=notes or None,
    )
    db.add(expense)
    db.commit()
    return RedirectResponse("/expenses/", status_code=303)


@router.get("/{expense_id}", response_class=HTMLResponse)
def view_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)
    return templates.TemplateResponse("expenses/detail.html", {"request": request, "expense": expense})


@router.get("/{expense_id}/edit", response_class=HTMLResponse)
def edit_expense_form(expense_id: int, request: Request, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)
    centers = db.query(CostCenter).order_by(CostCenter.name).all()
    categories = db.query(ExpenseCategory).order_by(ExpenseCategory.name).all()
    return templates.TemplateResponse(
        "expenses/form.html",
        {"request": request, "expense": expense, "centers": centers, "categories": categories},
    )


@router.post("/{expense_id}/edit")
async def update_expense(
    expense_id: int,
    cost_center_id: int = Form(...),
    category_id: str = Form(""),
    expense_date: str = Form(...),
    description: str = Form(...),
    gross_amount: str = Form(...),
    vat_rate: str = Form("25.5"),
    notes: str = Form(""),
    receipt: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        return RedirectResponse("/expenses/", status_code=303)

    try:
        gross = Decimal(gross_amount.replace(",", "."))
        rate = Decimal(vat_rate.replace(",", "."))
    except InvalidOperation:
        return RedirectResponse(f"/expenses/{expense_id}/edit", status_code=303)

    vat_amount, net_amount = _compute_vat(gross, rate)

    expense.cost_center_id = cost_center_id
    expense.category_id = int(category_id) if category_id else None
    expense.date = date.fromisoformat(expense_date)
    expense.description = description
    expense.gross_amount = gross
    expense.vat_rate = rate
    expense.vat_amount = vat_amount
    expense.net_amount = net_amount
    expense.notes = notes or None

    if receipt and receipt.filename:
        new_filename = _save_receipt(receipt)
        if new_filename:
            # Remove old file if exists
            if expense.receipt_image_path:
                old_path = os.path.join(RECEIPTS_DIR, expense.receipt_image_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            expense.receipt_image_path = new_filename

    db.commit()
    return RedirectResponse("/expenses/", status_code=303)


@router.post("/{expense_id}/delete")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense:
        if expense.receipt_image_path:
            old_path = os.path.join(RECEIPTS_DIR, expense.receipt_image_path)
            if os.path.exists(old_path):
                os.remove(old_path)
        db.delete(expense)
        db.commit()
    return RedirectResponse("/expenses/", status_code=303)
