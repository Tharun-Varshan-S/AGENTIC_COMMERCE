from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.models.consent import ConsentRequest
from app.models.audit import AuditLog
from app.consent.schemas import ConsentRequestInput, ConsentRequestResponse
from app.policy.service import PolicyService
from app.policy.schemas import PolicyEvaluationRequest, PolicyDecision
import uuid

class ConsentService:
    def __init__(self, db: Session):
        self.db = db
        self.policy_service = PolicyService(db)

    def request_consent(self, req: ConsentRequestInput) -> ConsentRequestResponse:
        # 1. Run Policy Engine
        policy_req = PolicyEvaluationRequest(
            merchant_id=req.merchant_id,
            customer_id=req.customer_id,
            cart_id=req.cart_id
        )
        
        try:
            decision: PolicyDecision = self.policy_service.evaluate(policy_req)
        except Exception as e:
            return ConsentRequestResponse(status="ERROR", message=str(e))
            
        self._log_audit(req.merchant_id, req.customer_id, "SYSTEM", "POLICY_EVALUATED", {"decision": decision.decision})

        # 2. Return ALLOWED if not required
        if decision.decision == "ALLOWED":
            return ConsentRequestResponse(
                status="NOT_REQUIRED",
                decision="ALLOWED"
            )
            
        # 3. Return REJECTED if hard failure
        if decision.decision == "REJECTED":
            self._log_audit(req.merchant_id, req.customer_id, "SYSTEM", "POLICY_REJECTED", {"reasons": [r.code for r in decision.reasons]})
            return ConsentRequestResponse(
                status="REJECTED",
                decision="REJECTED",
                reasons=decision.reasons
            )
            
        # 4. Create Consent Request for REQUIRES_CONSENT
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=10) # 10 mins expiry
        
        consent = ConsentRequest(
            id=str(uuid.uuid4()),
            merchant_id=req.merchant_id,
            customer_id=req.customer_id,
            cart_id=req.cart_id,
            policy_decision=decision.decision,
            amount=decision.cart_total,
            status="PENDING",
            expires_at=expires_at
        )
        
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        
        self._log_audit(req.merchant_id, req.customer_id, "SYSTEM", "CONSENT_REQUESTED", {"consent_id": str(consent.id), "amount": float(consent.amount)})
        
        return ConsentRequestResponse(
            status="PENDING",
            decision="REQUIRES_CONSENT",
            consent_id=str(consent.id),
            amount=consent.amount,
            message="Customer approval required.",
            reasons=decision.reasons
        )
        
    def _get_consent(self, consent_id: str) -> ConsentRequest:
        return self.db.query(ConsentRequest).filter(ConsentRequest.id == consent_id).first()
        
    def approve(self, consent_id: str) -> ConsentRequestResponse:
        consent = self._get_consent(consent_id)
        if not consent:
            return ConsentRequestResponse(status="ERROR", message="Consent request not found")
            
        now = datetime.now(timezone.utc)
        
        # Ensure timezone-aware comparison
        expires_at = consent.expires_at
        if expires_at.tzinfo is None:
             expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now > expires_at:
            consent.status = "EXPIRED"
            self.db.commit()
            self._log_audit(consent.merchant_id, consent.customer_id, "SYSTEM", "CONSENT_EXPIRED", {"consent_id": consent.id})
            return ConsentRequestResponse(status="EXPIRED", message="Consent request has expired")
            
        if consent.status != "PENDING":
            return ConsentRequestResponse(status="ERROR", message=f"Consent request is in {consent.status} state")
            
        # Re-run policy to ensure it's still valid
        policy_req = PolicyEvaluationRequest(
            merchant_id=str(consent.merchant_id),
            customer_id=str(consent.customer_id),
            cart_id=str(consent.cart_id)
        )
        decision: PolicyDecision = self.policy_service.evaluate(policy_req)
        
        if decision.decision == "REJECTED":
            return ConsentRequestResponse(status="REJECTED", message="Policy now rejects this transaction", reasons=decision.reasons)
            
        if decision.cart_total != consent.amount:
            # Re-trigger consent process instead of approving
            return ConsentRequestResponse(status="ERROR", message="Cart amount has changed. Please request consent again.")
            
        consent.status = "APPROVED"
        consent.responded_at = now
        self.db.commit()
        
        self._log_audit(consent.merchant_id, consent.customer_id, "CUSTOMER", "CONSENT_APPROVED", {"consent_id": str(consent.id)})
        
        return ConsentRequestResponse(status="APPROVED", decision="ALLOWED", consent_id=str(consent.id))
        
    def decline(self, consent_id: str) -> ConsentRequestResponse:
        consent = self._get_consent(consent_id)
        if not consent:
            return ConsentRequestResponse(status="ERROR", message="Consent request not found")
            
        if consent.status != "PENDING":
            return ConsentRequestResponse(status="ERROR", message=f"Consent request is in {consent.status} state")
            
        consent.status = "DECLINED"
        consent.responded_at = datetime.now(timezone.utc)
        self.db.commit()
        
        self._log_audit(consent.merchant_id, consent.customer_id, "CUSTOMER", "CONSENT_DECLINED", {"consent_id": str(consent.id)})
        
        return ConsentRequestResponse(status="DECLINED", consent_id=str(consent.id))

    def _log_audit(self, merchant_id: str, customer_id: str, actor_type: str, action: str, details: dict = None):
        log = AuditLog(
            merchant_id=merchant_id,
            customer_id=customer_id,
            actor_type=actor_type,
            action=action,
            event_type="CONSENT_EVALUATION",
            metadata_json=details or {}
        )
        self.db.add(log)
        self.db.commit()
