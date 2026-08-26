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

    # Relationships
    merchant = relationship("Merchant", backref="users")
