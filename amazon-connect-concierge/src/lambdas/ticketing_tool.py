"""Support Ticketing Tool Lambda for Amazon Connect GenAI Concierge.

Supports direct Python imports (for MCP server), API Gateway HTTP API (POST /tickets/create),
and Amazon Bedrock Action Group payload formats with strict parameter validation.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("ticketing_tool")
logger.setLevel(logging.INFO)

VALID_CATEGORIES = {"RETURN", "EXCHANGE", "DAMAGED_ITEM", "SHIPPING_DELAY", "OTHER"}


def create_support_ticket(
    customer_id: str,
    issue_category: str,
    description: str,
    order_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create a support ticket or return request.
    
    Args:
        customer_id: Customer Profile ID or email address.
        issue_category: Classification category for the issue.
        description: Detailed explanation of the issue.
        order_id: Optional associated order identifier.
        
    Returns:
        Dictionary containing ticket details, status, priority, and resolution ETA.
    """
    category = issue_category.upper().strip() if issue_category else "OTHER"
    if category not in VALID_CATEGORIES:
        category = "OTHER"
        
    ticket_id = f"TICKET-{str(uuid.uuid4())[:8].upper()}"
    priority = "HIGH" if category in {"DAMAGED_ITEM", "SHIPPING_DELAY"} else "MEDIUM"
    
    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "order_id": order_id,
        "issue_category": category,
        "description": description,
        "status": "OPEN",
        "priority": priority,
        "estimated_resolution_hours": 24,
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler supporting API Gateway HTTP API and Bedrock Action Groups.
    
    Args:
        event: Lambda invocation event.
        context: Lambda execution context.
        
    Returns:
        HTTP response dict or Bedrock Action Group response envelope.
    """
    logger.info("Received support ticketing invocation event: %s", json.dumps(event))
    
    customer_id = None
    issue_category = None
    description = None
    order_id = None

    # 1. Amazon Bedrock Action Group Payload Detection
    if "actionGroup" in event:
        action_group = event.get("actionGroup", "")
        api_path = event.get("apiPath", "")
        http_method = event.get("httpMethod", "POST")
        
        request_body = event.get("requestBody", {}).get("content", {}).get("application/json", {})
        if "properties" in request_body:
            for prop in request_body.get("properties", []):
                p_name = prop.get("name")
                p_val = prop.get("value")
                if p_name == "customer_id":
                    customer_id = p_val
                elif p_name == "issue_category":
                    issue_category = p_val
                elif p_name == "description":
                    description = p_val
                elif p_name == "order_id":
                    order_id = p_val
        elif "body" in request_body:
            try:
                body_data = json.loads(request_body["body"])
                customer_id = body_data.get("customer_id")
                issue_category = body_data.get("issue_category")
                description = body_data.get("description")
                order_id = body_data.get("order_id")
            except Exception:
                pass
                
        for param in event.get("parameters", []):
            p_name = param.get("name")
            p_val = param.get("value")
            if p_name == "customer_id":
                customer_id = p_val
            elif p_name == "issue_category":
                issue_category = p_val
            elif p_name == "description":
                description = p_val
            elif p_name == "order_id":
                order_id = p_val

        if not customer_id or not issue_category or not description:
            return {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": action_group,
                    "apiPath": api_path,
                    "httpMethod": http_method,
                    "httpStatusCode": 400,
                    "responseBody": {
                        "application/json": {
                            "body": json.dumps({"error": "Missing required fields: customer_id, issue_category, description"})
                        }
                    }
                }
            }

        ticket_result = create_support_ticket(
            customer_id=customer_id,
            issue_category=issue_category,
            description=description,
            order_id=order_id
        )
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action_group,
                "apiPath": api_path,
                "httpMethod": http_method,
                "httpStatusCode": 201,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(ticket_result)
                    }
                }
            }
        }

    # 2. Standard API Gateway HTTP API / REST Payload
    if event.get("body"):
        try:
            body = json.loads(event["body"])
            customer_id = body.get("customer_id")
            issue_category = body.get("issue_category")
            description = body.get("description")
            order_id = body.get("order_id")
        except Exception as e:
            logger.warning("Failed to parse request body JSON: %s", str(e))

    if not customer_id or not issue_category or not description:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": "Missing required body fields: customer_id, issue_category, description"})
        }

    result = create_support_ticket(
        customer_id=customer_id,
        issue_category=issue_category,
        description=description,
        order_id=order_id
    )
    
    return {
        "statusCode": 201,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(result)
    }
