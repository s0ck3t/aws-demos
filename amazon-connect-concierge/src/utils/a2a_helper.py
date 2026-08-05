"""A2A Helper module for JSON-RPC 2.0 validation, Agent Cards loading, and protocol envelope formatting."""

import os
import json
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schemas"))


def load_agent_card(agent_type: str = "returns-specialist") -> Dict[str, Any]:
    """Load an Agent Card JSON specification based on agent_type."""
    filename_map = {
        "frontline-concierge": "agent_card_frontline.json",
        "agent-frontline-concierge": "agent_card_frontline.json",
        "returns-specialist": "agent_card_returns.json",
        "agent-returns-specialist": "agent_card_returns.json",
        "default": "agent_card_returns.json"
    }

    card_filename = filename_map.get(agent_type.lower(), "agent_card_returns.json")
    file_path = os.path.join(SCHEMA_DIR, card_filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Agent card file not found at path: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_handoff_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate an A2A Open Protocol payload.
    
    Supports both JSON-RPC 2.0 task request envelopes and direct task parameters.
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"

    # Check if payload is a JSON-RPC 2.0 Envelope
    if payload.get("jsonrpc") == "2.0":
        if "method" not in payload:
            return False, "JSON-RPC 2.0 request missing 'method'"
        params = payload.get("params")
        if not isinstance(params, dict):
            return False, "JSON-RPC 2.0 request 'params' must be an object"
        data_to_check = params
    else:
        data_to_check = payload

    required_fields = ["session_id", "origin_agent_id", "target_agent_id", "customer_profile", "context_snapshot"]
    for field in required_fields:
        if field not in data_to_check:
            return False, f"Missing required field: '{field}'"

    profile = data_to_check.get("customer_profile", {})
    if not isinstance(profile, dict) or "profile_id" not in profile or "email" not in profile:
        return False, "Invalid 'customer_profile': must contain 'profile_id' and 'email'"

    context = data_to_check.get("context_snapshot", {})
    if not isinstance(context, dict) or "intent" not in context or "dialogue_summary" not in context:
        return False, "Invalid 'context_snapshot': must contain 'intent' and 'dialogue_summary'"

    return True, "Payload valid"


def format_a2a_response(status_code: int, message: str, body: Dict[str, Any], req_id: Optional[Any] = "1") -> Dict[str, Any]:
    """Format standard API Gateway HTTP response wrapping JSON-RPC 2.0 envelope."""
    is_error = status_code >= 400
    jsonrpc_envelope = {
        "jsonrpc": "2.0",
        "id": req_id or "1"
    }

    if is_error:
        jsonrpc_envelope["error"] = {
            "code": -32600 if status_code == 400 else -32603,
            "message": message,
            "data": body
        }
    else:
        jsonrpc_envelope["result"] = {
            "message": message,
            "data": body
        }

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-A2A-Version": "1.0.0",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        },
        "body": json.dumps(jsonrpc_envelope)
    }
