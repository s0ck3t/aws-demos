"""CDK Stack Assertion tests for ConciergeA2AGatewayStack (A2A Open Protocol v1.0 Compliant)."""

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template, Match
from infra.stacks.security_stack import SecurityStack
from infra.stacks.a2a_stack import A2AGatewayStack


@pytest.fixture
def a2a_stack_template():
    """Synthesize ConciergeA2AGatewayStack into CloudFormation template."""
    app = App()
    env = Environment(account="123456789012", region="eu-west-2")

    sec_stack = SecurityStack(app, "TestSecurityStack", env=env)
    a2a_stack = A2AGatewayStack(
        app,
        "TestA2AGatewayStack",
        env=env,
        encryption_key=sec_stack.encryption_key,
        lambda_role=sec_stack.lambda_execution_role
    )

    return Template.from_stack(a2a_stack)


def test_cognito_user_pool_creation(a2a_stack_template):
    """Verify Cognito User Pool is created with strict sign-up rules."""
    a2a_stack_template.has_resource_properties(
        "AWS::Cognito::UserPool",
        {
            "UserPoolName": "ConnectConcierge-A2AUserPool",
            "AdminCreateUserConfig": {
                "AllowAdminCreateUserOnly": True
            }
        }
    )


def test_cognito_resource_server_scopes(a2a_stack_template):
    """Verify Resource Server defines custom scopes for A2A handoff and read."""
    a2a_stack_template.has_resource_properties(
        "AWS::Cognito::UserPoolResourceServer",
        {
            "Identifier": "a2a",
            "Name": "Agent-to-Agent Mesh Gateway",
            "Scopes": Match.array_with([
                Match.object_like({"ScopeName": "handoff"}),
                Match.object_like({"ScopeName": "read"})
            ])
        }
    )


def test_cognito_user_pool_client_flows(a2a_stack_template):
    """Verify App Client enables Client Credentials OAuth2 flow."""
    a2a_stack_template.has_resource_properties(
        "AWS::Cognito::UserPoolClient",
        {
            "ClientName": "A2AMeshClient",
            "AllowedOAuthFlows": ["client_credentials"],
            "AllowedOAuthScopes": Match.array_with(["a2a/handoff", "a2a/read"])
        }
    )


def test_api_gateway_http_api_routes(a2a_stack_template):
    """Verify API Gateway HTTP API contains routes for A2A Open Protocol endpoints."""
    a2a_stack_template.has_resource_properties(
        "AWS::ApiGatewayV2::Api",
        {
            "Name": "ConnectConcierge-A2AGatewayApi",
            "ProtocolType": "HTTP"
        }
    )

    # Check Routes exist for A2A Open Protocol v1.0
    a2a_stack_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {"RouteKey": "GET /.well-known/agent.json"}
    )
    a2a_stack_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {"RouteKey": "POST /a2a/tasks"}
    )
    a2a_stack_template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {"RouteKey": "POST /a2a/handoff"}
    )


def test_lambda_functions_created(a2a_stack_template):
    """Verify A2ARouter and ReturnsSpecialist Lambda functions exist."""
    a2a_stack_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"FunctionName": "ConnectConcierge-A2ARouter"}
    )
    a2a_stack_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"FunctionName": "ConnectConcierge-ReturnsSpecialist"}
    )
