"""Returns & Refunds Specialist Agent Lambda Function (A2A Open Protocol v1.0 Compliant).

Executes return valuation, RMA creation, and refund authorisation, returning
structured A2A Open Protocol task outputs.
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
    # Handle JSON-RPC 2.0 params envelope or direct payload
    params = payload.get("params", payload) if isinstance(payload, dict) else {}
    
    task_id = params.get("task_id", f"task-{uuid.uuid4().hex[:8]}")
    session_id = params.get("session_id", str(uuid.uuid4()))
    profile = params.get("customer_profile", {})
    context = params.get("context_snapshot", {})

    order_id = context.get("order_id", "ORD-UNKNOWN")
    sku = context.get("sku", "SKU-UNKNOWN")
    item_price_gbp = float(context.get("item_price_gbp", 0.0))
    fraud_risk_score = float(context.get("fraud_risk_score", 0.05))

    logger.info("Evaluating A2A return task %s for customer %s, order %s, risk %.2f",
                task_id, profile.get("email"), order_id, fraud_risk_score)

    # Policy Check 1: Fraud Risk Gate
    if fraud_risk_score > 0.80:
        return {
            "task_id": task_id,
            "session_id": session_id,
            "status": "REJECTED",
            "decision": "REJECTED_MANUAL_REVIEW",
            "reason": "Fraud risk score exceeds automated authorisation threshold.",
            "refund_authorised": False,
            "refund_amount_gbp": 0.00
        }

    # Generate unique RMA and Label URL
    rma_code = f"RMA-2026-{uuid.uuid4().hex[:8].upper()}"
    label_url = f"https://shipping.concierge.internal/labels/{rma_code}.pdf"

    return {
        "task_id": task_id,
        "session_id": session_id,
        "status": "COMPLETED",
        "decision": "RETURN_AUTHORISED",
        "rma_number": rma_code,
        "customer_email": profile.get("email"),
        "order_id": order_id,
        "sku": sku,
        "refund_authorised": True,
        "refund_amount_gbp": item_price_gbp,
        "currency": "GBP",
        "return_shipping_label_url": label_url,
        "instructions": "Attach the return label to your original packaging and drop off at any Royal Mail post office.",
        "specialist_agent_id": "agent-returns-specialist",
        "protocol": "A2A_OPEN_PROTOCOL_v1.0"
    }


def handler(event, context):
    """Lambda handler for Returns Specialist Agent."""
    logger.info("Returns Specialist invoked with event: %s", json.dumps(event))

    # Determine if event is wrapped in API Gateway request
    if isinstance(event, dict) and "body" in event:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        req_id = body.get("id", "req-1") if isinstance(body, dict) else "req-1"
        result = process_return_request(body)
        return format_a2a_response(200, "Return request processed successfully by Returns Specialist", result, req_id=req_id)
    
    result = process_return_request(event if isinstance(event, dict) else {})
    return result
