#!/usr/bin/env python3
"""Custom Model Context Protocol (MCP) Server for E-Commerce Tooling.

Exposes inventory lookup and support ticketing tools to Agentic IDEs (Antigravity, Kiro, Cursor)
and foundation model runtimes using the standard MCP JSON-RPC 2.0 protocol over stdio.
"""

import sys
import json
import logging
from typing import Dict, Any, List

# Add parent lambdas path to import business logic directly
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambdas"))

from inventory_tool import get_inventory_status
from ticketing_tool import create_support_ticket

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp_server_ecommerce")

# Define MCP Tool Schemas
MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "check_inventory",
        "description": "Check real-time stock levels, warehouse lead times, and nearby store availability for a product SKU.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sku": {
                    "type": "string",
                    "description": "The stock keeping unit identifier (e.g. SKU-1001, SKU-1002)"
                }
            },
            "required": ["sku"]
        }
    },
    {
        "name": "create_support_ticket",
        "description": "Open a customer support ticket or return/exchange request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer identifier or email address"
                },
                "issue_category": {
                    "type": "string",
                    "enum": ["RETURN", "EXCHANGE", "DAMAGED_ITEM", "SHIPPING_DELAY", "OTHER"],
                    "description": "Classification category for the issue"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed explanation of the issue"
                },
                "order_id": {
                    "type": "string",
                    "description": "Optional associated order identifier"
                }
            },
            "required": ["customer_id", "issue_category", "description"]
        }
    }
]


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Process incoming MCP JSON-RPC requests.
    
    Args:
        request: Parsed JSON-RPC request payload.
        
    Returns:
        JSON-RPC response dictionary.
    """
    msg_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    # Protocol initialization handshakes
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "ecommerce-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    elif method == "notifications/initialized":
        # Notification response (no ID returned)
        return None
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "check_inventory":
            sku = arguments.get("sku")
            if not sku:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: Missing required 'sku' parameter."
                    }
                }
            result = get_inventory_status(sku)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        elif tool_name == "create_support_ticket":
            customer_id = arguments.get("customer_id")
            issue_category = arguments.get("issue_category")
            description = arguments.get("description")
            order_id = arguments.get("order_id")
            
            if not customer_id or not issue_category or not description:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: Missing required fields ('customer_id', 'issue_category', 'description')."
                    }
                }
            
            result = create_support_ticket(customer_id, issue_category, description, order_id)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool '{tool_name}' not found."
                }
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not supported."
            }
        }


def main():
    """Stdio loop for receiving JSON-RPC requests from an Agentic IDE."""
    logger.info("Starting E-Commerce MCP Server (stdio)...")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as e:
            logger.error("Error processing request: %s", str(e))
            err_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
