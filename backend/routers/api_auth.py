from fastapi import APIRouter, Depends, HTTPException, status, Response, Form, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from ..database import get_db
from ..models import User, Customer, Provider, DeliveryAgent, UserRole, UserStatus, VerificationStatus, AgentStatus, DeliveryVerification
from ..dependencies import hash_password as get_password_hash, verify_password, create_access_token, get_current_user_from_request as get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------
# REGISTRATION (Uses Form fields for HTML forms)
# ---------------------------------------------------------

@router.post("/register")
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    phone: str = Form(...),
    address: Optional[str] = Form(None),
    mess_name: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    cuisine_type: Optional[str] = Form(None),
    operating_hours: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    vehicle_type: Optional[str] = Form(None),
    license_number: Optional[str] = Form(None),
    service_area: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role_map = {"customer": UserRole.customer, "provider": UserRole.provider,
                "delivery": UserRole.delivery, "admin": UserRole.admin}
    user_role = role_map.get(role, UserRole.customer)
    
    user = User(name=name, email=email, password_hash=get_password_hash(password), role=user_role)
    db.add(user)
    db.flush() # Flush to get user.id before commit

    if user_role == UserRole.customer:
        p = Customer(user_id=user.id, phone=phone, address=address)
        db.add(p)
    elif user_role == UserRole.provider:
        p = Provider(user_id=user.id, mess_name=mess_name or name,
                     cuisine_type=cuisine_type, location=location,
                     phone=phone, verification_status=VerificationStatus.pending,
                     operating_hours=operating_hours, description=description)
        db.add(p)
    elif user_role == UserRole.delivery:
        p = DeliveryAgent(user_id=user.id, phone=phone, vehicle_type=vehicle_type,
                          service_area=service_area, license_number=license_number,
                          verification_status=DeliveryVerification.pending,
                          availability=AgentStatus.offline)
        db.add(p)
    
    db.commit()
    db.refresh(user)
    
    # Auto-login after registration
    from fastapi.responses import RedirectResponse
    from datetime import timedelta
    
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}, expires_delta=access_token_expires
    )
    
    redirect_url = "/customer/home"
    if user.role == UserRole.provider:
        redirect_url = "/provider/dashboard"
    elif user.role == UserRole.delivery:
        redirect_url = "/delivery/dashboard"
    elif user.role == UserRole.admin:
        redirect_url = "/admin/dashboard"
        
    res = RedirectResponse(url=redirect_url, status_code=303)
    res.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=1440 * 60,
        secure=False,
        path="/"
    )
    return res

# ---------------------------------------------------------
# LOGIN (Uses OAuth2PasswordRequestForm standard or Form)
# ---------------------------------------------------------

@router.post("/login")
async def login(
    response: Response, 
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    # 'username' is used universally in OAuth2 standards for the email field
    user = db.query(User).filter(User.email == username).first()
    if not user or not verify_password(password, user.password_hash):
        from fastapi.responses import RedirectResponse
        import urllib.parse
        err = urllib.parse.quote("Invalid email or password.")
        return RedirectResponse(url=f"/login?error={err}", status_code=303)
        
    if user.status == UserStatus.blocked:
        from fastapi.responses import RedirectResponse
        import urllib.parse
        err = urllib.parse.quote("Account has been blocked by admin.")
        return RedirectResponse(url=f"/login?error={err}", status_code=303)

    # Calculate token expiry
    access_token_expires = timedelta(minutes=1440) # 24 hours
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}, expires_delta=access_token_expires
    )

    # Redirect based on role instead of returning JSON
    from fastapi.responses import RedirectResponse
    redirect_url = "/customer/home"
    if user.role.value == "provider":
        redirect_url = "/provider/dashboard"
    elif user.role.value == "delivery":
        redirect_url = "/delivery/dashboard"
    elif user.role.value == "admin":
        redirect_url = "/admin/dashboard"

    res = RedirectResponse(url=redirect_url, status_code=303)
    # Set as HTTP-Only Cookie for SSR routing protection
    res.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=1440 * 60,
        secure=False,  # Set to True in HTTPS production
        path="/"
    )

    return res

# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"message": "Logged out"}

@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    from backend.dependencies import get_current_user_from_request
    user = get_current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role.value}
