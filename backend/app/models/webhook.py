from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base_class import BaseModel

class WebhookEvent(BaseModel):
    __tablename__ = "webhook_events"

    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=True)
    payload = Column(JSONB, nullable=False)
    signature_valid = Column(Boolean, default=True)
    processed = Column(Boolean, default=False, index=True)
    processing_error = Column(String, nullable=True)
    processed_at = Column(DateTime, nullable=True)
