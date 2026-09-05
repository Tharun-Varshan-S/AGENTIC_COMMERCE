from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False, default="CUSTOMER") # CUSTOMER, MERCHANT_OWNER, MERCHANT_ADMIN, MERCHANT_OPERATOR, PLATFORM_ADMIN
    is_active = Column(Boolean, default=True)
    merchant_id = Column(ForeignKey("merchants.id"), nullable=True, index=True)
    # Razorpay tokenization fields — stored once per user, used for headless agent charges
    razorpay_customer_id = Column(String, nullable=True)       # cust_xxx from Razorpay
    active_mandate_token = Column(String, nullable=True)       # token_xxx saved during one-time setup

    # Relationships
    merchant = relationship("Merchant", backref="users")

class UserSpendingLimit(BaseModel):
    __tablename__ = "user_spending_limits"
    
    user_id = Column(ForeignKey("users.id"), unique=True, index=True, nullable=False)
    daily_limit = Column(String, nullable=False, default="10000") # stored as string to match decimal patterns if needed, or integer
    
    user = relationship("User", backref="spending_limit")
