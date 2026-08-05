"""Returns & Refunds Specialist Agent Lambda Function.

Simulates a Bedrock Agent Core / domain specialist agent executing return valuation,
RMA creation, and return label generation.
"""

import os
import json
import logging
import uuid
from typing import Dict, Any

try:
    from utils.a2a_helper import format_a2a_response
except ImportError:
    try:
        from src.utils.a2a_helper import format_a2a_response
    except ImportError:
        from a2a_helper import format_a2a_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def process_return_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute business rules for e-commerce return valuation and RMA creation."""
    session_id = payload.get("session_id", str(uuid.uuid4()))
    profile = payload.get("customer_profile", {})
    context = payload.get("context_snapshot", {})

    order_id = context.get("order_id", "ORD-UNKNOWN")
    sku = context.get("sku", "SKU-UNKNOWN")
    item_price_gbp = float(context.get("item_price_gbp", 0.0))
    fraud_risk_score = float(context.get("fraud_risk_score", 0.05))

    logger.info("Evaluating return for customer %s, order %s, sku %s, risk %.2f",
                profile.get("email"), order_id, sku, fraud_risk_score)

    # Policy Check 1: Fraud Risk Gate
    if fraud_risk_score > 0.80:
        return {
            "session_id": session_id,
            "decision": "REJECTED_MANUAL_REVIEW",
            "reason": "Fraud risk score exceeds automated authorization threshold.",
            "refund_authorized": False,
            "refund_amount_gbp": 0.00
        }

    # Generate unique RMA and Label URL
    rma_code = f"RMA-2026-{uuid.uuid4().hex[:8].upper()}"
    label_url = f"https://shipping.concierge.internal/labels/{rma_code}.pdf"

    return {
        "session_id": session_id,
        "decision": "RETURN_AUTHORIZED",
        "rma_number": rma_code,
        "customer_email": profile.get("email"),
        "order_id": order_id,
        "sku": sku,
        "refund_authorized": True,
        "refund_amount_gbp": item_price_gbp,
        "currency": "GBP",
        "return_shipping_label_url": label_url,
        "instructions": "Attach the return label to your original packaging and drop off at any Royal Mail post office.",
        "specialist_agent_id": "agent-returns-specialist",
        "execution_timestamp": "2026-08-05T16:31:00Z"
    }


def handler(event, context):
    """Lambda handler for Returns Specialist Agent."""
    logger.info("Returns Specialist invoked with event: %s", json.dumps(event))

    # Determine if event is raw payload or API Gateway event
    if isinstance(event, dict) and "body" in event:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        result = process_return_request(body)
        return format_a2a_response(200, "Return request processed successfully by Returns Specialist", result)
    
    result = process_return_request(event if isinstance(event, dict) else {})
    return result
