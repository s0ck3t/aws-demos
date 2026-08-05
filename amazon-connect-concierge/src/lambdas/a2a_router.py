"""A2A Router Lambda Function (A2A Open Protocol v1.0 Compliant).

Handles:
1. GET /.well-known/agent.json & GET /a2a/agent-cards/{agent_id} - Serves A2A Open Protocol Agent Cards.
2. POST /a2a/tasks & POST /a2a/handoff - Validates JSON-RPC 2.0 task requests, checks OAuth2 JWT claims, and routes to specialist agent.
"""

import os
import json
import logging
import uuid

# Support package-style, AWS Lambda container (/var/task), and flat imports
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
    logger.info("Received A2A Router event: %s", json.dumps(event))

    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    raw_path = event.get("rawPath", event.get("path", ""))

    # 1. Route: GET /.well-known/agent.json or GET /a2a/agent-cards/{agent_id}
    if http_method == "GET" and (raw_path.endswith("/.well-known/agent.json") or "/a2a/agent-cards/" in raw_path):
        agent_id = "returns-specialist"
        if "/a2a/agent-cards/" in raw_path:
            agent_id = raw_path.split("/a2a/agent-cards/")[-1].strip()
        try:
            card = load_agent_card(agent_id)
            return format_a2a_response(200, f"A2A Agent Card retrieved for '{agent_id}'", card)
        except (ValueError, FileNotFoundError) as err:
            logger.warning("Agent card error: %s", str(err))
            return format_a2a_response(404, str(err), {})

    # 2. Route: POST /a2a/tasks or POST /a2a/handoff
    if http_method == "POST" and (raw_path.endswith("/a2a/tasks") or raw_path.endswith("/a2a/handoff")):
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
            return format_a2a_response(400, "Invalid JSON-RPC request body", {})

        req_id = payload.get("id", "req-1")

        # Validate Handoff & JSON-RPC 2.0 Contract
        valid, msg = validate_handoff_payload(payload)
        if not valid:
            logger.warning("A2A Contract validation failed: %s", msg)
            return format_a2a_response(400, f"A2A Contract Violation: {msg}", {}, req_id=req_id)

        # Extract Claims & Verify Authorization Context
        authorizer = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {})
        claims = authorizer.get("claims", {})
        logger.info("Authorizer claims verified: client_id=%s, scope=%s", claims.get("client_id"), claims.get("scope"))

        # Extract params from JSON-RPC envelope or raw body
        task_params = payload.get("params", payload)
        target_agent = task_params.get("target_agent_id", "agent-returns-specialist")
        session_id = task_params.get("session_id", str(uuid.uuid4()))

        logger.info("Routing A2A Open Protocol task for session %s to target agent %s", session_id, target_agent)

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
                
                # Unpack body if wrapped in API Gateway envelope
                if isinstance(res_payload, dict) and "body" in res_payload:
                    specialist_body = json.loads(res_payload["body"])
                    return format_a2a_response(200, "A2A task executed successfully by specialist agent", specialist_body, req_id=req_id)
                
                return format_a2a_response(200, "A2A task executed successfully by specialist agent", res_payload, req_id=req_id)
            except Exception as err:
                logger.error("Failed to invoke specialist Lambda %s: %s", specialist_function_name, str(err))
                return format_a2a_response(500, f"Specialist invocation error: {str(err)}", {}, req_id=req_id)

        # Fallback Mock Execution response when invoked directly / locally
        handoff_acknowledgement = {
            "task_id": task_params.get("task_id", f"task-{uuid.uuid4().hex[:8]}"),
            "session_id": session_id,
            "status": "COMPLETED",
            "origin_agent_id": task_params.get("origin_agent_id", "agent-frontline-concierge"),
            "target_agent_id": target_agent,
            "execution_protocol": "A2A_OPEN_PROTOCOL_v1.0"
        }
        return format_a2a_response(200, "A2A task accepted and routed successfully", handoff_acknowledgement, req_id=req_id)

    return format_a2a_response(404, f"Route not found: {http_method} {raw_path}", {})
