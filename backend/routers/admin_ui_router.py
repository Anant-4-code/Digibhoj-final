from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dependencies import get_current_user_from_request
from backend.models import User
import os

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

# Define the hidden, secure route requested by the user
router = APIRouter(prefix="/admin-super-control-portal-x9k2-secure", tags=["admin_ui"])

# Custom dependency for strictly enforcing ADMIN role
def require_admin(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user:
        # Redirect to login if not authenticated
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})
    if user.role.value != "admin":
        # Strictly return 403 Forbidden for non-admins
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to access the control panel.")
    return user

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "user": user})

@router.get("/users", response_class=HTMLResponse)
def admin_users(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/users.html", {"request": request, "user": user})

@router.get("/verifications", response_class=HTMLResponse)
def admin_verifications(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/verifications.html", {"request": request, "user": user})

@router.get("/orders", response_class=HTMLResponse)
def admin_orders(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/orders.html", {"request": request, "user": user})

@router.get("/reviews", response_class=HTMLResponse)
def admin_reviews(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/reviews.html", {"request": request, "user": user})

@router.get("/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/analytics.html", {"request": request, "user": user})

@router.get("/database", response_class=HTMLResponse)
def admin_database(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/database.html", {"request": request, "user": user})

@router.get("/logs", response_class=HTMLResponse)
def admin_logs(request: Request, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/logs.html", {"request": request, "user": user})
