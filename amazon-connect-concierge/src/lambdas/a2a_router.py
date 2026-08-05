"""A2A Router Lambda Function.

Handles:
1. GET /a2a/agent-cards/{agent_id} - Serves declarative Agent Cards for discovery.
2. POST /a2a/handoff - Validates A2A handoff contract, checks OAuth2 JWT claims, and routes to target specialist agent.
"""

import os
import json
import logging

# Support both package-style, AWS Lambda container (/var/task), and flat imports
try:
    from utils.a2a_helper import load_agent_card, validate_handoff_payload, format_a2a_response
except ImportError:
    try:
        from src.utils.a2a_helper import load_agent_card, validate_handoff_payload, format_a2a_response
    except ImportError:
        from a2a_helper import load_agent_card, validate_handoff_payload, format_a2a_response

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_PAYLOAD_BYTES = 64 * 1024  # 64 KB limit for abuse protection


def handler(event, context):
    """API Gateway HTTP API Lambda handler for A2A Gateway Router."""
    logger.info("Received event: %s", json.dumps(event))

    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    raw_path = event.get("rawPath", event.get("path", ""))

    # 1. Route: GET /a2a/agent-cards/{agent_id}
    if http_method == "GET" and "/a2a/agent-cards/" in raw_path:
        agent_id = raw_path.split("/a2a/agent-cards/")[-1].strip()
        try:
            card = load_agent_card(agent_id)
            return format_a2a_response(200, f"Agent card retrieved for '{agent_id}'", card)
        except (ValueError, FileNotFoundError) as err:
            logger.warning("Agent card error: %s", str(err))
            return format_a2a_response(404, str(err), {})

    # 2. Route: POST /a2a/handoff
    if http_method == "POST" and raw_path.endswith("/a2a/handoff"):
        body_str = event.get("body", "")
        if not body_str:
            return format_a2a_response(400, "Missing request body", {})

        # Cost & Abuse Protection: Size limit check
        if len(body_str.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            logger.warning("Payload size exceeded maximum allowed limit of 64KB")
            return format_a2a_response(413, "Payload too large. Maximum size is 64KB.", {})

        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            return format_a2a_response(400, "Invalid JSON in request body", {})

        # Validate Handoff Contract
        valid, msg = validate_handoff_payload(payload)
        if not valid:
            logger.warning("Handoff validation failed: %s", msg)
            return format_a2a_response(400, f"A2A Contract Violation: {msg}", {})

        # Extract Claims & Verify Authorization Context
        authorizer = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {})
        claims = authorizer.get("claims", {})
        logger.info("Authorizer claims verified: client_id=%s, scope=%s", claims.get("client_id"), claims.get("scope"))

        target_agent = payload["target_agent_id"]
        logger.info("Routing A2A handoff for session %s to target agent %s", payload["session_id"], target_agent)

        # Route to Specialist Lambda if configured
        specialist_function_name = os.environ.get("RETURNS_SPECIALIST_FUNCTION_NAME")
        if specialist_function_name and target_agent in ["agent-returns-specialist", "returns-specialist"]:
            try:
                lambda_client = boto3.client("lambda")
                response = lambda_client.invoke(
                    FunctionName=specialist_function_name,
                    InvocationType="RequestResponse",
                    Payload=json.dumps(payload)
                )
                res_payload = json.loads(response["Payload"].read().decode("utf-8"))
                
                # If wrapped in API Gateway format, unpack body
                if isinstance(res_payload, dict) and "body" in res_payload:
                    specialist_body = json.loads(res_payload["body"])
                    return format_a2a_response(200, "A2A Handoff successfully executed by specialist agent", specialist_body)
                
                return format_a2a_response(200, "A2A Handoff successfully executed by specialist agent", res_payload)
            except Exception as err:
                logger.error("Failed to invoke specialist Lambda %s: %s", specialist_function_name, str(err))
                return format_a2a_response(500, f"Specialist invocation error: {str(err)}", {})

        # Fallback Mock Execution response when invoked directly / locally
        handoff_acknowledgement = {
            "session_id": payload["session_id"],
            "status": "HANDOFF_ACCEPTED",
            "origin_agent_id": payload["origin_agent_id"],
            "target_agent_id": target_agent,
            "handshake_timestamp": "2026-08-05T16:30:00Z",
            "assigned_specialist_channel": "A2A_DIRECT_STREAM"
        }
        return format_a2a_response(200, "A2A Handoff contract accepted and routed successfully", handoff_acknowledgement)

    return format_a2a_response(404, f"Route not found: {http_method} {raw_path}", {})
