from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
import jwt
from jwt.exceptions import InvalidTokenError

from app.db.session import get_db
from app.models.merchant import Merchant
from app.models.user import User
from app.core.security import verify_password, create_access_token, SECRET_KEY, ALGORITHM

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    merchant_id: str | None
    merchant_name: str | None = None

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalars(select(User).filter(User.email == req.email)).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
        
    user = db.scalars(select(User).filter(User.email == email)).first()
    if user is None:
        raise credentials_exception
    return user

@router.get("/me", response_model=UserProfile)
def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    merchant_name = None
    if current_user.merchant_id:
        merchant = db.scalars(select(Merchant).filter(Merchant.id == current_user.merchant_id)).first()
        if merchant:
            merchant_name = merchant.name

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "merchant_id": str(current_user.merchant_id) if current_user.merchant_id else None,
        "merchant_name": merchant_name
    }

def get_current_merchant_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Merchant:
    if not current_user.merchant_id:
        raise HTTPException(status_code=403, detail="Not associated with a merchant")
    if not current_user.role.startswith("MERCHANT_"):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    merchant = db.scalars(select(Merchant).filter(Merchant.id == current_user.merchant_id)).first()
    if not merchant or not merchant.is_active:
        raise HTTPException(status_code=404, detail="Merchant not found or inactive")
    return merchant

def get_demo_merchant(db: Session = Depends(get_db)) -> Merchant:
    """Deprecated: used only for fallback/demo scripts where auth is not passed."""
    merchant = db.scalars(select(Merchant).filter(Merchant.name == "TechNova Gaming Store", Merchant.is_active == True)).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No active TechNova merchant found")
    return merchant
