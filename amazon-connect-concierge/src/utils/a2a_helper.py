"""A2A Helper module for payload validation, Agent Cards loading, and handoff envelope formatting."""

import os
import json
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SCHEMA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schemas"))


def load_agent_card(agent_type: str) -> Dict[str, Any]:
    """Load an Agent Card JSON specification based on agent_type."""
    filename_map = {
        "frontline-concierge": "agent_card_frontline.json",
        "agent-frontline-concierge": "agent_card_frontline.json",
        "returns-specialist": "agent_card_returns.json",
        "agent-returns-specialist": "agent_card_returns.json"
    }

    card_filename = filename_map.get(agent_type.lower())
    if not card_filename:
        raise ValueError(f"Unknown agent type or card identifier: {agent_type}")

    file_path = os.path.join(SCHEMA_DIR, card_filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Agent card file not found at path: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_handoff_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate a handoff payload against contract rules.
    
    Checks required top-level fields and nested objects.
    """
    required_fields = ["session_id", "origin_agent_id", "target_agent_id", "customer_profile", "context_snapshot"]
    for field in required_fields:
        if field not in payload:
            return False, f"Missing required top-level field: '{field}'"

    profile = payload.get("customer_profile", {})
    if not isinstance(profile, dict) or "profile_id" not in profile or "email" not in profile:
        return False, "Invalid 'customer_profile': must contain 'profile_id' and 'email'"

    context = payload.get("context_snapshot", {})
    if not isinstance(context, dict) or "intent" not in context or "dialogue_summary" not in context:
        return False, "Invalid 'context_snapshot': must contain 'intent' and 'dialogue_summary'"

    return True, "Payload valid"


def format_a2a_response(status_code: int, message: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Format standard API Gateway HTTP response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-A2A-Version": "1.0.0",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        },
        "body": json.dumps({
            "message": message,
            "data": body
        })
    }
