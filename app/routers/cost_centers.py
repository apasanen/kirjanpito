from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostCenter, Expense

router = APIRouter(prefix="/cost-centers", tags=["cost-centers"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def list_cost_centers(request: Request, db: Session = Depends(get_db)):
    centers = db.query(CostCenter).order_by(CostCenter.name).all()
    return templates.TemplateResponse(request, "cost_centers/list.html", {"request": request, "centers": centers})


@router.post("/new")
def create_cost_center(
    name: str = Form(...),
    type: str = Form("other"),
    description: str = Form(""),
    vat_deductible: str = Form(""),
    db: Session = Depends(get_db),
):
    name = name.strip()
    if not name:
        return RedirectResponse("/cost-centers/", status_code=303)
    center = CostCenter(
        name=name,
        type=type if type in ("apartment", "forest", "other") else "other",
        description=description.strip() or None,
        vat_deductible=bool(vat_deductible),
        active=True,
    )
    db.add(center)
    db.commit()
    return RedirectResponse("/cost-centers/", status_code=303)


@router.get("/{center_id}/edit", response_class=HTMLResponse)
def edit_cost_center_form(center_id: int, request: Request, db: Session = Depends(get_db)):
    center = db.query(CostCenter).filter(CostCenter.id == center_id).first()
    if not center:
        return RedirectResponse("/cost-centers/", status_code=303)
    return templates.TemplateResponse(request, "cost_centers/edit.html", {"request": request, "center": center})


@router.post("/{center_id}/edit")
def update_cost_center(
    center_id: int,
    name: str = Form(...),
    type: str = Form("other"),
    description: str = Form(""),
    vat_deductible: str = Form(""),
    active: str = Form(""),
    db: Session = Depends(get_db),
):
    center = db.query(CostCenter).filter(CostCenter.id == center_id).first()
    if not center:
        return RedirectResponse("/cost-centers/", status_code=303)
    center.name = name.strip()
    center.type = type if type in ("apartment", "forest", "other") else "other"
    center.description = description.strip() or None
    center.vat_deductible = bool(vat_deductible)
    center.active = bool(active)
    db.commit()
    return RedirectResponse("/cost-centers/", status_code=303)


@router.post("/{center_id}/delete")
def delete_cost_center(center_id: int, db: Session = Depends(get_db)):
    center = db.query(CostCenter).filter(CostCenter.id == center_id, CostCenter.active == False).first()
    if center:
        has_expenses = db.query(Expense).filter(Expense.cost_center_id == center_id).first()
        if not has_expenses:
            db.delete(center)
            db.commit()
    return RedirectResponse("/cost-centers/", status_code=303)
