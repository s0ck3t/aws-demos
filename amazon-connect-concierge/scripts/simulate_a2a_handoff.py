"""Simulate End-to-End Agent-to-Agent (A2A) Handoff Journey.

Executes:
1. Local schema validation and Agent Card discovery.
2. OAuth2 Client Credentials M2M Authentication token request (if AWS Cognito parameters provided).
3. A2A Handoff Request from Frontline Concierge Agent to Returns Specialist Agent.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.parse
from typing import Dict, Any

# Ensure UTF-8 stdout encoding on Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.a2a_helper import load_agent_card, validate_handoff_payload
from src.lambdas.a2a_router import handler as router_handler
from src.lambdas.returns_specialist_agent import handler as specialist_handler


def run_local_simulation():
    """Run local memory simulation of A2A handoff flow."""
    print("\n=======================================================")
    print("[+] [Step 1/3] A2A Agent Card Discovery (Local Spec)")
    print("=======================================================")
    
    frontline_card = load_agent_card("agent-frontline-concierge")
    returns_card = load_agent_card("agent-returns-specialist")

    print(f"[OK] Loaded Frontline Card: '{frontline_card['name']}' (Role: {frontline_card['role']})")
    print(f"[OK] Loaded Returns Specialist Card: '{returns_card['name']}' (Role: {returns_card['role']})")

    print("\n=======================================================")
    print("[+] [Step 2/3] Constructing A2A Handoff Contract Payload")
    print("=======================================================")

    handoff_contract = {
        "session_id": "connect-session-20260805-77",
        "origin_agent_id": frontline_card["agent_id"],
        "target_agent_id": returns_card["agent_id"],
        "customer_profile": {
            "profile_id": "prof-alex-dev-001",
            "email": "alex.dev@example.com",
            "phone_number": "+447700900123",
            "first_name": "Alex",
            "last_name": "Dev"
        },
        "context_snapshot": {
            "intent": "RETURN_ITEM_DAMAGED",
            "dialogue_summary": "Customer called reporting defective wireless headphones (£49.99). Frontline agent verified identity via Customer Profiles and initiated return delegation.",
            "order_id": "ORD-UK-2026-8819",
            "sku": "AUDIO-HEADSET-PRO",
            "return_reason": "DEFECTIVE_AUDIO",
            "item_price_gbp": 49.99,
            "purchase_date": "2026-07-28T14:20:00Z",
            "fraud_risk_score": 0.04
        }
    }

    valid, msg = validate_handoff_payload(handoff_contract)
    print(f"[OK] Payload Contract Validation: {msg}")
    print("Payload Content:\n", json.dumps(handoff_contract, indent=2))

    print("\n=======================================================")
    print("[+] [Step 3/3] Simulating A2A Router Execution")
    print("=======================================================")

    mock_apigw_event = {
        "requestContext": {
            "http": {"method": "POST"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "client_id": "test-a2a-m2m-client",
                        "scope": "a2a/handoff"
                    }
                }
            }
        },
        "rawPath": "/a2a/handoff",
        "body": json.dumps(handoff_contract)
    }

    router_response = router_handler(mock_apigw_event, None)
    print(f"[OK] A2A Router Response Code: {router_response['statusCode']}")
    body_data = json.loads(router_response['body'])
    print("Response Data:\n", json.dumps(body_data, indent=2))

    # Also directly invoke Returns Specialist handler for full end-to-end verification
    specialist_response = specialist_handler(handoff_contract, None)
    print("\n=======================================================")
    print("[+] [Specialist Execution] Returns Agent Valuation Result")
    print("=======================================================")
    print(json.dumps(specialist_response, indent=2))
    print("\n[OK] Local A2A Simulation completed successfully.")


def run_live_aws_simulation(api_endpoint: str, token_endpoint: str, client_id: str, client_secret: str):
    """Run live simulation against deployed AWS Cognito and API Gateway endpoints."""
    print("\n=======================================================")
    print("[+] [AWS Step 1/3] Requesting OAuth2 M2M Access Token from Cognito")
    print("=======================================================")

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    data = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": "a2a/handoff a2a/read"}).encode("utf-8")

    req = urllib.request.Request(
        token_endpoint,
        data=data,
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            tok_res = json.loads(resp.read().decode("utf-8"))
            access_token = tok_res.get("access_token")
            print(f"[OK] Token acquired successfully! Expires in: {tok_res.get('expires_in')}s")
            print(f"     Scope granted: {tok_res.get('scope')}")
    except Exception as err:
        print(f"[ERROR] Failed to acquire OAuth2 token from Cognito: {str(err)}")
        return

    print("\n=======================================================")
    print("[+] [AWS Step 2/3] Fetching Agent Card via API Gateway")
    print("=======================================================")

    card_url = f"{api_endpoint.rstrip('/')}/a2a/agent-cards/returns-specialist"
    req_card = urllib.request.Request(card_url, method="GET")
    try:
        with urllib.request.urlopen(req_card) as resp:
            card_data = json.loads(resp.read().decode("utf-8"))
            print("[OK] Agent Card Retrieved:\n", json.dumps(card_data, indent=2))
    except Exception as err:
        print(f"[WARN] Agent card fetch failed: {str(err)}")

    print("\n=======================================================")
    print("[+] [AWS Step 3/3] Initiating A2A Handoff via API Gateway")
    print("=======================================================")

    handoff_url = f"{api_endpoint.rstrip('/')}/a2a/handoff"
    handoff_payload = {
        "session_id": "aws-connect-session-9901",
        "origin_agent_id": "agent-frontline-concierge",
        "target_agent_id": "agent-returns-specialist",
        "customer_profile": {
            "profile_id": "prof-aws-001",
            "email": "alex.dev@example.com",
            "phone_number": "+447700900123"
        },
        "context_snapshot": {
            "intent": "RETURN_ITEM",
            "dialogue_summary": "Customer requested return authorization for audio headset (£49.99).",
            "order_id": "ORD-UK-9921",
            "sku": "AUDIO-HEADSET-PRO",
            "item_price_gbp": 49.99,
            "fraud_risk_score": 0.05
        }
    }

    handoff_req = urllib.request.Request(
        handoff_url,
        data=json.dumps(handoff_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(handoff_req) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            print("[OK] A2A Handoff Executed Successfully!\n", json.dumps(res_body, indent=2))
    except Exception as err:
        print(f"[ERROR] A2A Handoff request failed: {str(err)}")


if __name__ == "__main__":
    api_ep = os.environ.get("A2A_API_ENDPOINT")
    tok_ep = os.environ.get("A2A_TOKEN_ENDPOINT")
    client_id = os.environ.get("A2A_CLIENT_ID")
    client_sec = os.environ.get("A2A_CLIENT_SECRET")

    if api_ep and tok_ep and client_id and client_sec:
        print("Using live AWS Endpoints from environment variables...")
        run_live_aws_simulation(api_ep, tok_ep, client_id, client_sec)
    else:
        print("No live AWS credentials provided in environment variables. Running local in-memory simulation...")
        run_local_simulation()
