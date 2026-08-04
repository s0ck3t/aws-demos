"""Tooling Stack for Amazon Connect Omnichannel AI Concierge.

Provisions zero-baseline cost infrastructure:
- Lambda functions for inventory lookup and support ticketing.
- API Gateway HTTP API routes (/inventory/{sku} and /tickets/create).
- Amazon Bedrock Guardrail (CfnGuardrail & CfnGuardrailVersion) with PII anonymisation,
  sensitive topic denial, and contextual grounding filters.
"""

import os
from aws_cdk import Stack, Duration, RemovalPolicy
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_apigatewayv2 as apigw2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

LAMBDA_ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "lambdas"))


class ToolingStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        encryption_key: kms.IKey,
        lambda_role: iam.IRole,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Lambda Functions for Tools
        self.inventory_fn = lambda_.Function(
            self,
            "InventoryToolFunction",
            function_name="ConnectConcierge-InventoryTool",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="inventory_tool.handler",
            code=lambda_.Code.from_asset(LAMBDA_ASSET_DIR),
            role=lambda_role,
            timeout=Duration.seconds(10),
            log_group=logs.LogGroup(
                self,
                "InventoryToolLogGroup",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment={"LOG_LEVEL": "INFO"}
        )

        self.ticketing_fn = lambda_.Function(
            self,
            "TicketingToolFunction",
            function_name="ConnectConcierge-TicketingTool",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="ticketing_tool.handler",
            code=lambda_.Code.from_asset(LAMBDA_ASSET_DIR),
            role=lambda_role,
            timeout=Duration.seconds(10),
            log_group=logs.LogGroup(
                self,
                "TicketingToolLogGroup",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment={"LOG_LEVEL": "INFO"}
        )

        # 2. Serverless API Gateway HTTP API (Zero-Baseline Cost with Rate Limiting)
        self.http_api = apigw2.HttpApi(
            self,
            "ConciergeToolsHttpApi",
            api_name="ConnectConcierge-ToolsApi",
            description="Serverless HTTP API for E-Commerce Inventory and Ticketing Tools"
        )

        # Configure Stage-Level Rate Limiting (10 req/sec, burst 20) on default stage
        if self.http_api.default_stage and self.http_api.default_stage.node.default_child:
            cfn_stage: apigw2.CfnStage = self.http_api.default_stage.node.default_child
            cfn_stage.default_route_settings = apigw2.CfnStage.RouteSettingsProperty(
                throttling_rate_limit=10,
                throttling_burst_limit=20
            )

        # HTTP API Lambda Integrations
        inventory_integration = integrations.HttpLambdaIntegration(
            "InventoryToolIntegration",
            self.inventory_fn
        )

        ticketing_integration = integrations.HttpLambdaIntegration(
            "TicketingToolIntegration",
            self.ticketing_fn
        )

        # Add Routes: GET /inventory/{sku} and POST /tickets/create
        self.http_api.add_routes(
            path="/inventory/{sku}",
            methods=[apigw2.HttpMethod.GET],
            integration=inventory_integration
        )

        self.http_api.add_routes(
            path="/tickets/create",
            methods=[apigw2.HttpMethod.POST],
            integration=ticketing_integration
        )

        # 3. Amazon Bedrock Guardrail (CfnGuardrail)
        self.guardrail = bedrock.CfnGuardrail(
            self,
            "ConciergeBedrockGuardrail",
            name="ConnectConcierge-SafetyGuardrail",
            description="Enterprise safety guardrail for Amazon Connect Concierge enforcing PII masking and grounding.",
            kms_key_arn=encryption_key.key_arn,
            blocked_input_messaging="I am unable to process this input as it violates enterprise security policies.",
            blocked_outputs_messaging="I am unable to provide this output as it violates enterprise security policies.",
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="EMAIL",
                        action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="PHONE",
                        action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="UK_NATIONAL_INSURANCE_NUMBER",
                        action="ANONYMIZE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="CREDIT_DEBIT_CARD_NUMBER",
                        action="BLOCK"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        type="UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER",
                        action="BLOCK"
                    )
                ]
            ),
            topic_policy_config=bedrock.CfnGuardrail.TopicPolicyConfigProperty(
                topics_config=[
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="unauthorized-financial-advice",
                        definition="Providing non-compliant financial or investment advice, pricing guarantees, or banking instructions.",
                        type="DENY"
                    ),
                    bedrock.CfnGuardrail.TopicConfigProperty(
                        name="competitor-comparison",
                        definition="Direct comparison or endorsement of competing e-commerce platforms and non-partner retailers.",
                        type="DENY"
                    )
                ]
            ),
            contextual_grounding_policy_config=bedrock.CfnGuardrail.ContextualGroundingPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContextualGroundingFilterConfigProperty(
                        type="GROUNDING",
                        threshold=0.85
                    ),
                    bedrock.CfnGuardrail.ContextualGroundingFilterConfigProperty(
                        type="RELEVANCE",
                        threshold=0.80
                    )
                ]
            )
        )

        # 4. Amazon Bedrock Guardrail Version (CfnGuardrailVersion)
        self.guardrail_version = bedrock.CfnGuardrailVersion(
            self,
            "ConciergeBedrockGuardrailVersion",
            guardrail_identifier=self.guardrail.attr_guardrail_id,
            description="Production version v2 of Amazon Connect Concierge Safety Guardrail with UK PII filters"
        )
