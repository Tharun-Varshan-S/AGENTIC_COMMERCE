from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
import jwt
from jwt.exceptions import InvalidTokenError

from app.db.session import get_db
from app.models.merchant import Merchant, MerchantAPIKey
from app.models.user import User
from app.models.customer import Customer
from app.core.security import verify_password, create_access_token, SECRET_KEY, ALGORITHM
import hashlib

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    redirect_url: str | None = None

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
    redirect_url = "/merchant/dashboard" if user.role.startswith("MERCHANT_") else "/buyer"
    return {"access_token": access_token, "redirect_url": redirect_url}

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

def get_current_customer_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    if current_user.role not in ["CUSTOMER", "MERCHANT_ADMIN", "MERCHANT_OWNER", "PLATFORM_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

def verify_customer_ownership(db: Session, customer_id: str, current_user: User):
    customer = db.scalars(select(Customer).filter(Customer.id == customer_id)).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.email != current_user.email:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this customer's resources")
    return customer

def resolve_customer(db: Session, current_user: User, merchant_id: str, provided_customer_id: str | None = None) -> Customer:
    if provided_customer_id:
        return verify_customer_ownership(db, provided_customer_id, current_user)
    
    customer = db.scalars(select(Customer).filter(
        Customer.email == current_user.email,
        Customer.merchant_id == merchant_id
    )).first()
    
    if not customer:
        customer = Customer(
            email=current_user.email,
            name=current_user.full_name or current_user.email.split("@")[0],
            merchant_id=merchant_id
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
    
    return customer

def get_demo_merchant(db: Session = Depends(get_db)) -> Merchant:
    """Deprecated: used only for fallback/demo scripts where auth is not passed."""
    merchant = db.scalars(select(Merchant).filter(Merchant.name == "TechNova Gaming Store", Merchant.is_active == True)).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No active TechNova merchant found")
    return merchant

def get_merchant_api_key_or_user(request: Request, db: Session = Depends(get_db)) -> Merchant:
    api_key_header = request.headers.get("x-api-key")
    if api_key_header:
        # Validate API Key
        key_hash = hashlib.sha256(api_key_header.encode()).hexdigest()
        api_key = db.query(MerchantAPIKey).filter(
            MerchantAPIKey.key_hash == key_hash,
            MerchantAPIKey.is_active == True
        ).first()
        
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API Key")
            
        merchant = api_key.merchant
        if not merchant or not merchant.is_active:
            raise HTTPException(status_code=403, detail="Merchant not found or inactive")
        return merchant
        
    # Fallback to JWT auth
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication credentials")
        
    token = auth_header.split(" ")[1]
    user = get_current_user(token=token, db=db)
    return get_current_merchant_user(current_user=user, db=db)
