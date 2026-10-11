from datetime import date
import re
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import extract
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import CostCenter, Expense

router = APIRouter(prefix="/receipts", tags=["receipts"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def list_receipts(
    request: Request,
    cost_center_id: Optional[str] = None,
    year: Optional[str] = None,
    search_regex: Optional[str] = None,
    db: Session = Depends(get_db),
):
    selected_center = int(cost_center_id) if cost_center_id else None
    selected_year = int(year) if year else None

    query = db.query(Expense).options(joinedload(Expense.cost_center)).filter(
        Expense.receipt_image_path.isnot(None),
        Expense.receipt_image_path != "",
    )
    if selected_center:
        query = query.filter(Expense.cost_center_id == selected_center)
    if selected_year:
        query = query.filter(
            Expense.date >= date(selected_year, 1, 1),
            Expense.date <= date(selected_year, 12, 31),
        )

    receipts = query.order_by(Expense.date.desc(), Expense.id.desc()).all()
    search_error = None
    if search_regex:
        try:
            pattern = re.compile(search_regex, re.IGNORECASE)
        except re.error as error:
            receipts = []
            search_error = f"Virheellinen regex: {error}"
        else:
            receipts = [
                expense
                for expense in receipts
                if pattern.search(
                    " ".join(
                        (
                            expense.reference or "",
                            expense.description or "",
                            expense.receipt_image_path or "",
                            expense.cost_center.name,
                        )
                    )
                )
            ]
    centers = (
        db.query(CostCenter)
        .join(Expense, Expense.cost_center_id == CostCenter.id)
        .filter(Expense.receipt_image_path.isnot(None), Expense.receipt_image_path != "")
        .distinct()
        .order_by(CostCenter.name)
        .all()
    )
    years = [
        int(row.year)
        for row in db.query(extract("year", Expense.date).label("year"))
        .filter(Expense.receipt_image_path.isnot(None), Expense.receipt_image_path != "")
        .distinct()
        .order_by(extract("year", Expense.date).desc())
        .all()
        if row.year is not None
    ]
    return_params = []
    if selected_center:
        return_params.append(("cost_center_id", str(selected_center)))
    if selected_year:
        return_params.append(("year", str(selected_year)))
    if search_regex:
        return_params.append(("search_regex", search_regex))
    return_to = "/receipts/" + ("?" + urlencode(return_params) if return_params else "")

    return templates.TemplateResponse(
        request,
        "receipts/list.html",
        {
            "request": request,
            "receipts": receipts,
            "centers": centers,
            "years": years,
            "selected_center": selected_center,
            "selected_year": selected_year,
            "search_regex": search_regex or "",
            "search_error": search_error,
            "edit_return_to": urlencode({"return_to": return_to}),
        },
    )