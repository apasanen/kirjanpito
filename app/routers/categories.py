from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expense, ExpenseCategory, ExpenseLine

router = APIRouter(prefix="/categories", tags=["categories"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def list_categories(request: Request, db: Session = Depends(get_db)):
    categories = db.query(ExpenseCategory).order_by(ExpenseCategory.category_type, ExpenseCategory.name).all()
    # Count expenses per category for display
    counts = {}
    for cat in categories:
        counts[cat.id] = db.query(ExpenseLine).filter(ExpenseLine.category_id == cat.id).count()
    return templates.TemplateResponse(
        request,
        "categories/list.html",
        {"request": request, "categories": categories, "counts": counts},
    )


@router.post("/new")
def create_category(name: str = Form(...), category_type: str = Form("expense"), db: Session = Depends(get_db)):
    name = name.strip()
    category_type = category_type if category_type in ("expense", "income") else "expense"
    if name and not db.query(ExpenseCategory).filter(
        ExpenseCategory.name == name,
        ExpenseCategory.category_type == category_type,
    ).first():
        db.add(ExpenseCategory(name=name, category_type=category_type))
        db.commit()
    return RedirectResponse("/categories/", status_code=303)


@router.post("/{cat_id}/rename")
def rename_category(cat_id: int, name: str = Form(...), db: Session = Depends(get_db)):
    name = name.strip()
    cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == cat_id).first()
    if cat and name:
        cat.name = name
        db.commit()
    return RedirectResponse("/categories/", status_code=303)


@router.post("/{cat_id}/delete")
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    cat = db.query(ExpenseCategory).filter(ExpenseCategory.id == cat_id).first()
    if cat:
        # Unlink lines before deleting
        db.query(ExpenseLine).filter(ExpenseLine.category_id == cat_id).update({"category_id": None})
        db.delete(cat)
        db.commit()
    return RedirectResponse("/categories/", status_code=303)
