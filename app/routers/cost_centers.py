from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CostCenter

router = APIRouter(prefix="/cost-centers", tags=["cost-centers"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def list_cost_centers(request: Request, db: Session = Depends(get_db)):
    centers = db.query(CostCenter).order_by(CostCenter.name).all()
    return templates.TemplateResponse("cost_centers/list.html", {"request": request, "centers": centers})
