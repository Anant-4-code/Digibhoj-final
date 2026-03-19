from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Cookie, Request
from sqlalchemy.orm import Session
from backend.database import get_db

SECRET_KEY = "digibhoj-super-secret-key-2024-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user_from_request(request: Request, db: Session = Depends(get_db)):
    from backend.models import User
    token = request.cookies.get("access_token")
    if not token:
        # print("DEBUG AUTH: No access_token cookie found")
        return None
    
    # Strip quotes if added by some clients/middleware
    token = token.strip('"').replace("Bearer ", "")
    payload = decode_token(token)
    if not payload:
        print(f"DEBUG AUTH: Token decoding failed for: {token[:10]}...")
        return None
        
    user_id = payload.get("sub")
    if not user_id:
        print("DEBUG AUTH: No 'sub' in payload")
        return None
        
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            print(f"DEBUG AUTH: User ID {user_id} not found in DB")
        return user
    except (ValueError, TypeError) as e:
        print(f"DEBUG AUTH: Invalid user_id format in token: {user_id}")
        return None

def require_role(role: str):
    def dependency(request: Request, db: Session = Depends(get_db)):
        user = get_current_user_from_request(request, db)
        if not user:
            from fastapi.responses import RedirectResponse
            raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/login"})
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"Access denied. Required role: {role}")
        return user
    return dependency

def require_customer(request: Request, db: Session = Depends(get_db)):
    return require_role("customer")(request, db)

def require_provider(request: Request, db: Session = Depends(get_db)):
    return require_role("provider")(request, db)

def require_delivery(request: Request, db: Session = Depends(get_db)):
    return require_role("delivery")(request, db)

def require_admin(request: Request, db: Session = Depends(get_db)):
    return require_role("admin")(request, db)
