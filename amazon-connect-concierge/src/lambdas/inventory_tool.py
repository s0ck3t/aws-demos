"""Inventory Lookup Tool Lambda for Amazon Connect GenAI Concierge.

Supports direct Python imports (for MCP server), API Gateway HTTP API (GET /inventory/{sku}),
and Amazon Bedrock Action Group payload formats with strict parameter validation.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger("inventory_tool")
logger.setLevel(logging.INFO)

# In-memory mock inventory database
INVENTORY_DATABASE: Dict[str, Dict[str, Any]] = {
    "SKU-1001": {
        "sku": "SKU-1001",
        "product_name": "Ergonomic Mesh Executive Chair",
        "stock_level": 42,
        "status": "IN_STOCK",
        "fulfillment_lead_days": 1,
        "nearby_store_availability": True
    },
    "SKU-1002": {
        "sku": "SKU-1002",
        "product_name": "Wireless Active Noise Cancelling Headset",
        "stock_level": 5,
        "status": "LOW_STOCK",
        "fulfillment_lead_days": 2,
        "nearby_store_availability": True
    },
    "SKU-1003": {
        "sku": "SKU-1003",
        "product_name": "Motorized Adjustable Standing Desk",
        "stock_level": 0,
        "status": "OUT_OF_STOCK",
        "fulfillment_lead_days": 7,
        "nearby_store_availability": False
    }
}


def get_inventory_status(sku: str) -> Dict[str, Any]:
    """Retrieve stock level and lead times for a given product SKU.
    
    Args:
        sku: Stock Keeping Unit string identifier.
        
    Returns:
        Dictionary containing stock level, status, lead days, and store availability.
    """
    normalized_sku = sku.upper().strip() if sku else ""
    if normalized_sku in INVENTORY_DATABASE:
        return INVENTORY_DATABASE[normalized_sku]
    
    # Generic status resolution for unlisted SKUs
    return {
        "sku": sku,
        "product_name": f"Standard Retail Item ({sku})",
        "stock_level": 15,
        "status": "IN_STOCK",
        "fulfillment_lead_days": 2,
        "nearby_store_availability": True
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler supporting API Gateway HTTP API and Bedrock Action Groups.
    
    Args:
        event: Lambda invocation event.
        context: Lambda execution context.
        
    Returns:
        HTTP response dict or Bedrock Action Group response envelope.
    """
    logger.info("Received inventory lookup invocation event: %s", json.dumps(event))
    
    # 1. Amazon Bedrock Action Group Payload Detection
    if "actionGroup" in event:
        action_group = event.get("actionGroup", "")
        api_path = event.get("apiPath", "")
        http_method = event.get("httpMethod", "GET")
        
        sku = None
        parameters = event.get("parameters", [])
        for param in parameters:
            if param.get("name") == "sku":
                sku = param.get("value")
                break

        if not sku:
            return {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": action_group,
                    "apiPath": api_path,
                    "httpMethod": http_method,
                    "httpStatusCode": 400,
                    "responseBody": {
                        "application/json": {
                            "body": json.dumps({"error": "Missing required parameter 'sku'"})
                        }
                    }
                }
            }
                
        inventory_result = get_inventory_status(sku)
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(inventory_result)
                    }
                }
            }
        }

    # 2. Standard API Gateway HTTP API / REST Payload
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    
    sku = path_params.get("sku") or query_params.get("sku")
    
    if not sku and event.get("body"):
        try:
            body = json.loads(event["body"])
            sku = body.get("sku")
        except Exception:
            pass

    if not sku:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": "Missing required path parameter 'sku'"})
        }
        
    result = get_inventory_status(sku)
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(result)
    }
