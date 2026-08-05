"""Pytest Unit test suite for A2A Router and Returns Specialist Lambda functions."""

import json
import pytest
from src.utils.a2a_helper import load_agent_card, validate_handoff_payload, format_a2a_response
from src.lambdas.a2a_router import handler as router_handler
from src.lambdas.returns_specialist_agent import handler as specialist_handler, process_return_request


def test_load_agent_cards():
    """Verify loading Frontline and Returns agent cards."""
    frontline_card = load_agent_card("agent-frontline-concierge")
    assert frontline_card["agent_id"] == "agent-frontline-concierge"
    assert frontline_card["role"] == "FRONTLINE_TRIAGE"

    returns_card = load_agent_card("agent-returns-specialist")
    assert returns_card["agent_id"] == "agent-returns-specialist"
    assert returns_card["role"] == "RETURNS_SPECIALIST"


def test_validate_handoff_payload_valid():
    """Verify valid handoff contract payload passes validation."""
    payload = {
        "session_id": "test-session-123",
        "origin_agent_id": "agent-frontline-concierge",
        "target_agent_id": "agent-returns-specialist",
        "customer_profile": {
            "profile_id": "prof-001",
            "email": "alex.dev@example.com"
        },
        "context_snapshot": {
            "intent": "RETURN_ITEM",
            "dialogue_summary": "Customer wants to return defective wireless headphones."
        }
    }
    valid, msg = validate_handoff_payload(payload)
    assert valid is True
    assert msg == "Payload valid"


def test_validate_handoff_payload_missing_field():
    """Verify invalid payload missing required fields is rejected."""
    payload = {
        "session_id": "test-session-123",
        "origin_agent_id": "agent-frontline-concierge"
    }
    valid, msg = validate_handoff_payload(payload)
    assert valid is False
    assert "Missing required top-level field" in msg


def test_returns_specialist_valuation_authorized():
    """Verify returns specialist authorizes refund for low-risk request in GBP (£)."""
    payload = {
        "session_id": "sess-456",
        "customer_profile": {
            "email": "sarah.smith@example.co.uk"
        },
        "context_snapshot": {
            "order_id": "ORD-9912",
            "sku": "SKU-AUDIO-01",
            "item_price_gbp": 49.99,
            "fraud_risk_score": 0.05
        }
    }
    res = process_return_request(payload)
    assert res["decision"] == "RETURN_AUTHORIZED"
    assert res["refund_authorized"] is True
    assert res["refund_amount_gbp"] == 49.99
    assert res["currency"] == "GBP"
    assert res["rma_number"].startswith("RMA-2026-")


def test_returns_specialist_valuation_high_risk():
    """Verify high-risk request (>0.80) is routed for manual review."""
    payload = {
        "session_id": "sess-789",
        "customer_profile": {
            "email": "suspicious@example.com"
        },
        "context_snapshot": {
            "order_id": "ORD-8811",
            "fraud_risk_score": 0.92
        }
    }
    res = process_return_request(payload)
    assert res["decision"] == "REJECTED_MANUAL_REVIEW"
    assert res["refund_authorized"] is False
    assert res["refund_amount_gbp"] == 0.00


def test_a2a_router_get_agent_card():
    """Verify A2A Router handles GET /a2a/agent-cards/{agent_id}."""
    event = {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/a2a/agent-cards/returns-specialist"
    }
    res = router_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["data"]["agent_id"] == "agent-returns-specialist"


def test_a2a_router_post_handoff_valid():
    """Verify A2A Router accepts POST /a2a/handoff with valid payload."""
    payload = {
        "session_id": "sess-999",
        "origin_agent_id": "agent-frontline-concierge",
        "target_agent_id": "agent-returns-specialist",
        "customer_profile": {
            "profile_id": "prof-77",
            "email": "customer@example.com"
        },
        "context_snapshot": {
            "intent": "RETURN_ITEM",
            "dialogue_summary": "Return requested for size exchange"
        }
    }
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/a2a/handoff",
        "body": json.dumps(payload)
    }
    res = router_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert "A2A Handoff" in body["message"]
