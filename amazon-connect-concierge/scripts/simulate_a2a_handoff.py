"""Simulate End-to-End Agent-to-Agent (A2A) Open Protocol v1.0 Journey.

Executes:
1. Agent Card Discovery via standard URI /.well-known/agent.json.
2. OAuth2 Client Credentials M2M Authentication token request from Cognito.
3. JSON-RPC 2.0 Task Execution Request (method: tasks/send) from Frontline Agent to Returns Specialist Agent.
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
    """Run local memory simulation of A2A Open Protocol flow."""
    print("\n=======================================================")
    print("[+] [Step 1/3] A2A Agent Card Discovery (/.well-known/agent.json)")
    print("=======================================================")
    
    frontline_card = load_agent_card("agent-frontline-concierge")
    returns_card = load_agent_card("agent-returns-specialist")

    print(f"[OK] Loaded Frontline Card: '{frontline_card['name']}' (Protocol: {frontline_card.get('protocol_version', '1.0')})")
    print(f"[OK] Loaded Returns Specialist Card: '{returns_card['name']}' (Protocol: {returns_card.get('protocol_version', '1.0')})")

    print("\n=======================================================")
    print("[+] [Step 2/3] Constructing JSON-RPC 2.0 A2A Task Request Envelope")
    print("=======================================================")

    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "task_id": "task-20260805-001",
            "session_id": "connect-session-20260805-77",
            "origin_agent_id": frontline_card["name"],
            "target_agent_id": returns_card["name"],
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
        },
        "id": "req-8801"
    }

    valid, msg = validate_handoff_payload(jsonrpc_request)
    print(f"[OK] JSON-RPC 2.0 Payload Validation: {msg}")
    print("Request Envelope:\n", json.dumps(jsonrpc_request, indent=2))

    print("\n=======================================================")
    print("[+] [Step 3/3] Simulating A2A Router JSON-RPC Execution")
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
        "rawPath": "/a2a/tasks",
        "body": json.dumps(jsonrpc_request)
    }

    router_response = router_handler(mock_apigw_event, None)
    print(f"[OK] A2A Router HTTP Response Code: {router_response['statusCode']}")
    body_data = json.loads(router_response['body'])
    print("JSON-RPC 2.0 Response:\n", json.dumps(body_data, indent=2))

    specialist_response = specialist_handler(jsonrpc_request, None)
    print("\n=======================================================")
    print("[+] [Specialist Execution] A2A Open Protocol Task Output")
    print("=======================================================")
    print(json.dumps(specialist_response, indent=2))
    print("\n[OK] Local A2A Open Protocol v1.0 simulation completed successfully.")


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
    print("[+] [AWS Step 2/3] Fetching Agent Card (/.well-known/agent.json)")
    print("=======================================================")

    card_url = f"{api_endpoint.rstrip('/')}/.well-known/agent.json"
    req_card = urllib.request.Request(card_url, method="GET")
    try:
        with urllib.request.urlopen(req_card) as resp:
            card_data = json.loads(resp.read().decode("utf-8"))
            print("[OK] A2A Agent Card Retrieved:\n", json.dumps(card_data, indent=2))
    except Exception as err:
        print(f"[WARN] Agent card fetch failed: {str(err)}")

    print("\n=======================================================")
    print("[+] [AWS Step 3/3] Sending A2A Task via JSON-RPC 2.0 (POST /a2a/tasks)")
    print("=======================================================")

    tasks_url = f"{api_endpoint.rstrip('/')}/a2a/tasks"
    jsonrpc_payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "task_id": "aws-task-9901",
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
                "dialogue_summary": "Customer requested return authorisation for audio headset (£49.99).",
                "order_id": "ORD-UK-9921",
                "sku": "AUDIO-HEADSET-PRO",
                "item_price_gbp": 49.99,
                "fraud_risk_score": 0.05
            }
        },
        "id": "req-9901"
    }

    tasks_req = urllib.request.Request(
        tasks_url,
        data=json.dumps(jsonrpc_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(tasks_req) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            print("[OK] A2A JSON-RPC 2.0 Task Executed Successfully!\n", json.dumps(res_body, indent=2))
    except Exception as err:
        print(f"[ERROR] A2A Task request failed: {str(err)}")


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
