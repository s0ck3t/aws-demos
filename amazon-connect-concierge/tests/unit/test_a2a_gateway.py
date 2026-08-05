"""Pytest Unit test suite for A2A Router and Returns Specialist Lambda functions (A2A Open Protocol v1.0 Compliant)."""

import json
import pytest
from src.utils.a2a_helper import load_agent_card, validate_handoff_payload, format_a2a_response
from src.lambdas.a2a_router import handler as router_handler
from src.lambdas.returns_specialist_agent import handler as specialist_handler, process_return_request


def test_load_agent_cards_v1_0():
    """Verify loading A2A Open Protocol v1.0 Agent Cards."""
    frontline_card = load_agent_card("agent-frontline-concierge")
    assert frontline_card["protocol_version"] == "1.0"
    assert frontline_card["role"] == "FRONTLINE_TRIAGE"

    returns_card = load_agent_card("agent-returns-specialist")
    assert returns_card["protocol_version"] == "1.0"
    assert returns_card["role"] == "RETURNS_SPECIALIST"


def test_validate_jsonrpc2_payload_valid():
    """Verify valid JSON-RPC 2.0 A2A task payload passes validation."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "task_id": "task-001",
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
        },
        "id": "req-01"
    }
    valid, msg = validate_handoff_payload(payload)
    assert valid is True
    assert msg == "Payload valid"


def test_returns_specialist_valuation_authorized():
    """Verify returns specialist authorizes refund for low-risk request in GBP (£)."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "task_id": "task-999",
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
        },
        "id": "req-02"
    }
    res = process_return_request(payload)
    assert res["status"] == "COMPLETED"
    assert res["decision"] == "RETURN_AUTHORISED"
    assert res["refund_authorised"] is True
    assert res["refund_amount_gbp"] == 49.99
    assert res["currency"] == "GBP"
    assert res["rma_number"].startswith("RMA-2026-")


def test_a2a_router_get_well_known_agent_card():
    """Verify A2A Router handles GET /.well-known/agent.json."""
    event = {
        "requestContext": {"http": {"method": "GET"}},
        "rawPath": "/.well-known/agent.json"
    }
    res = router_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["jsonrpc"] == "2.0"
    assert body["result"]["data"]["protocol_version"] == "1.0"


def test_a2a_router_post_tasks_jsonrpc_valid():
    """Verify A2A Router accepts POST /a2a/tasks with JSON-RPC 2.0 payload."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "task_id": "task-777",
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
        },
        "id": "req-777"
    }
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/a2a/tasks",
        "body": json.dumps(payload)
    }
    res = router_handler(event, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["jsonrpc"] == "2.0"
    assert body["id"] == "req-777"
