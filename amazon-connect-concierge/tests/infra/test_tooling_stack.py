"""CDK Assertion tests for ToolingStack.

Validates AWS Lambda tool functions, API Gateway HTTP API routes, and Bedrock Guardrail configurations.
"""

import os
import sys
import pytest
import aws_cdk as cdk
from aws_cdk import assertions

# Add amazon-connect-concierge root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from infra.stacks.security_stack import SecurityStack
from infra.stacks.tooling_stack import ToolingStack


def test_tooling_stack_resources():
    app = cdk.App()
    security_stack = SecurityStack(app, "TestSecurityStack")
    tooling_stack = ToolingStack(
        app,
        "TestToolingStack",
        encryption_key=security_stack.encryption_key,
        lambda_role=security_stack.lambda_execution_role
    )
    template = assertions.Template.from_stack(tooling_stack)

    # 1. Verify 2 Lambda functions created (Inventory & Ticketing Tools)
    template.resource_count_is("AWS::Lambda::Function", 2)
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "ConnectConcierge-InventoryTool"
    })
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "ConnectConcierge-TicketingTool"
    })

    # 2. Verify Serverless API Gateway HTTP API and Routes
    template.resource_count_is("AWS::ApiGatewayV2::Api", 1)
    template.has_resource_properties("AWS::ApiGatewayV2::Api", {
        "Name": "ConnectConcierge-ToolsApi",
        "ProtocolType": "HTTP"
    })
    
    # Verify Stage Throttling (Rate Limit 10 req/sec, Burst 20)
    template.has_resource_properties("AWS::ApiGatewayV2::Stage", {
        "StageName": "$default",
        "DefaultRouteSettings": {
            "ThrottlingBurstLimit": 20,
            "ThrottlingRateLimit": 10
        }
    })

    # 3. Verify Amazon Bedrock Guardrail
    template.resource_count_is("AWS::Bedrock::Guardrail", 1)
    template.has_resource_properties("AWS::Bedrock::Guardrail", {
        "Name": "ConnectConcierge-SafetyGuardrail",
        "SensitiveInformationPolicyConfig": {
            "PiiEntitiesConfig": [
                {"Type": "EMAIL", "Action": "ANONYMIZE"},
                {"Type": "PHONE", "Action": "ANONYMIZE"},
                {"Type": "UK_NATIONAL_INSURANCE_NUMBER", "Action": "ANONYMIZE"},
                {"Type": "CREDIT_DEBIT_CARD_NUMBER", "Action": "BLOCK"},
                {"Type": "UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER", "Action": "BLOCK"}
            ]
        },
        "TopicPolicyConfig": {
            "TopicsConfig": [
                {
                    "Name": "unauthorized-financial-advice",
                    "Type": "DENY"
                },
                {
                    "Name": "competitor-comparison",
                    "Type": "DENY"
                }
            ]
        },
        "ContextualGroundingPolicyConfig": {
            "FiltersConfig": [
                {"Type": "GROUNDING", "Threshold": 0.85},
                {"Type": "RELEVANCE", "Threshold": 0.80}
            ]
        }
    })

    # 4. Verify Amazon Bedrock Guardrail Version
    template.resource_count_is("AWS::Bedrock::GuardrailVersion", 1)
