"""Unit tests for Inventory and Ticketing Lambda tools and MCP Server.

Validates core business logic, API Gateway HTTP API event handling,
Amazon Bedrock Action Group payloads, strict parameter validation (400 responses),
and MCP JSON-RPC protocol compliance.
"""

import os
import sys
import json
import pytest

# Ensure src/lambdas and src/mcp are accessible for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "lambdas")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "mcp")))

from inventory_tool import get_inventory_status, handler as inventory_handler
from ticketing_tool import create_support_ticket, handler as ticketing_handler
from mcp_server import handle_request


# --- 1. Inventory Tool Tests ---

def test_get_inventory_status_known_skus():
    res1 = get_inventory_status("SKU-1001")
    assert res1["status"] == "IN_STOCK"
    assert res1["stock_level"] == 42
    assert res1["fulfillment_lead_days"] == 1

    res2 = get_inventory_status("SKU-1002")
    assert res2["status"] == "LOW_STOCK"
    assert res2["stock_level"] == 5

    res3 = get_inventory_status("SKU-1003")
    assert res3["status"] == "OUT_OF_STOCK"
    assert res3["stock_level"] == 0


def test_get_inventory_status_unknown_sku():
    res = get_inventory_status("SKU-9999")
    assert res["sku"] == "SKU-9999"
    assert res["status"] == "IN_STOCK"
    assert res["stock_level"] == 15


def test_inventory_handler_api_gateway_event():
    event = {
        "pathParameters": {"sku": "SKU-1001"}
    }
    response = inventory_handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["sku"] == "SKU-1001"
    assert body["status"] == "IN_STOCK"


def test_inventory_handler_missing_sku_returns_400():
    event = {}
    response = inventory_handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_inventory_handler_bedrock_action_group_event():
    event = {
        "actionGroup": "InventoryActionGroup",
        "apiPath": "/inventory/{sku}",
        "httpMethod": "GET",
        "parameters": [
            {"name": "sku", "type": "string", "value": "SKU-1002"}
        ]
    }
    response = inventory_handler(event, None)
    assert response["messageVersion"] == "1.0"
    resp = response["response"]
    assert resp["httpStatusCode"] == 200
    body_data = json.loads(resp["responseBody"]["application/json"]["body"])
    assert body_data["sku"] == "SKU-1002"
    assert body_data["status"] == "LOW_STOCK"


# --- 2. Ticketing Tool Tests ---

def test_create_support_ticket_logic():
    res = create_support_ticket(
        customer_id="cust_test_01",
        issue_category="RETURN",
        description="Defective keyboard",
        order_id="ORD-5541"
    )
    assert res["ticket_id"].startswith("TICKET-")
    assert res["customer_id"] == "cust_test_01"
    assert res["status"] == "OPEN"
    assert res["priority"] == "MEDIUM"
    assert res["estimated_resolution_hours"] == 24


def test_create_support_ticket_high_priority():
    res = create_support_ticket(
        customer_id="cust_test_02",
        issue_category="DAMAGED_ITEM",
        description="Package arrived crushed"
    )
    assert res["priority"] == "HIGH"


def test_ticketing_handler_api_gateway_event():
    payload = {
        "customer_id": "cust_http_01",
        "issue_category": "EXCHANGE",
        "description": "Exchanging size M for size L",
        "order_id": "ORD-8812"
    }
    event = {
        "body": json.dumps(payload)
    }
    response = ticketing_handler(event, None)
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["customer_id"] == "cust_http_01"
    assert body["issue_category"] == "EXCHANGE"


def test_ticketing_handler_missing_fields_returns_400():
    payload = {"customer_id": "cust_incomplete"}
    event = {"body": json.dumps(payload)}
    response = ticketing_handler(event, None)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_ticketing_handler_bedrock_action_group_event():
    event = {
        "actionGroup": "TicketingActionGroup",
        "apiPath": "/tickets/create",
        "httpMethod": "POST",
        "requestBody": {
            "content": {
                "application/json": {
                    "body": json.dumps({
                        "customer_id": "cust_bedrock_01",
                        "issue_category": "SHIPPING_DELAY",
                        "description": "Package 3 days late"
                    })
                }
            }
        }
    }
    response = ticketing_handler(event, None)
    assert response["messageVersion"] == "1.0"
    resp = response["response"]
    assert resp["httpStatusCode"] == 201
    body_data = json.loads(resp["responseBody"]["application/json"]["body"])
    assert body_data["customer_id"] == "cust_bedrock_01"
    assert body_data["priority"] == "HIGH"


# --- 3. MCP Server JSON-RPC Protocol Tests ---

def test_mcp_initialize():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    resp = handle_request(req)
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "ecommerce-mcp-server"


def test_mcp_tools_list():
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    resp = handle_request(req)
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "check_inventory" in tool_names
    assert "create_support_ticket" in tool_names


def test_mcp_tools_call_inventory():
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "check_inventory",
            "arguments": {"sku": "SKU-1001"}
        }
    }
    resp = handle_request(req)
    assert resp["id"] == 3
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["sku"] == "SKU-1001"


def test_mcp_tools_call_inventory_missing_sku_returns_error():
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "check_inventory",
            "arguments": {}
        }
    }
    resp = handle_request(req)
    assert resp["error"]["code"] == -32602


def test_mcp_tools_call_ticketing():
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "create_support_ticket",
            "arguments": {
                "customer_id": "cust_mcp_1",
                "issue_category": "RETURN",
                "description": "Changed my mind"
            }
        }
    }
    resp = handle_request(req)
    assert resp["id"] == 4
    content = resp["result"]["content"][0]["text"]
    data = json.loads(content)
    assert data["customer_id"] == "cust_mcp_1"
    assert data["status"] == "OPEN"
