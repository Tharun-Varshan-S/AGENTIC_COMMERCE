from typing import Dict, Any, List
from app.policy.schemas import PolicyDecision, PolicyReason
from app.policy.rules import (
    MaxTransactionRule,
    InventoryRule,
    ProductStatusRule,
    PriceIntegrityRule,
    DiscountLimitRule,
    MinimumMarginRule,
    ConsentRequirementRule
)
from decimal import Decimal
from app.models.merchant import MerchantRule

class PolicyEvaluator:
    def __init__(self):
        # Order matters!
        self.hard_failure_rules = [
            ProductStatusRule(),
            InventoryRule(),
            DiscountLimitRule(),
            MinimumMarginRule(),
            MaxTransactionRule()
        ]
        self.consent_rules = [
            PriceIntegrityRule(),
            ConsentRequirementRule()
        ]

    def evaluate(self, context: Dict[str, Any]) -> PolicyDecision:
        cart_total: Decimal = context.get("cart_total", Decimal('0'))
        merchant_rules: MerchantRule = context.get("merchant_rules")
        auto_approval_limit = merchant_rules.auto_approval_limit if merchant_rules else None
        
        all_reasons = []
        
        # 1. Evaluate Hard Failures
        for rule in self.hard_failure_rules:
            reasons = rule.evaluate(context)
            all_reasons.extend(reasons)
            
        if all_reasons:
            return PolicyDecision(
                decision="REJECTED",
                allowed=False,
                requires_consent=False,
                reasons=all_reasons,
                cart_total=cart_total,
                auto_approval_limit=auto_approval_limit
            )
            
        # 2. Evaluate Consent Requirements
        for rule in self.consent_rules:
            reasons = rule.evaluate(context)
            all_reasons.extend(reasons)
            
        if all_reasons:
            return PolicyDecision(
                decision="REQUIRES_CONSENT",
                allowed=False,
                requires_consent=True,
                reasons=all_reasons,
                cart_total=cart_total,
                auto_approval_limit=auto_approval_limit
            )
            
        # 3. If no failures, it is ALLOWED
        return PolicyDecision(
            decision="ALLOWED",
            allowed=True,
            requires_consent=False,
            reasons=[],
            cart_total=cart_total,
            auto_approval_limit=auto_approval_limit
        )
