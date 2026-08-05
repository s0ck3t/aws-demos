"""A2A Gateway Infrastructure Stack for Amazon Connect Omnichannel AI Concierge (Part 3).

Provisions zero-baseline cost infrastructure:
- Cognito User Pool, Domain, Resource Server, and App Client with Client Credentials M2M OAuth2 Grant.
- Lambda Functions for A2A Router and Returns Specialist Agent.
- API Gateway HTTP API with Cognito JWT Authorizer and Stage-level Rate Limiting.
"""

import os
from aws_cdk import Stack, Duration, RemovalPolicy, CfnOutput
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_apigatewayv2 as apigw2
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_apigatewayv2_authorizers as authorizers
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

LAMBDA_ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "lambdas"))
UTILS_ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "utils"))
SCHEMAS_ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "schemas"))


class A2AGatewayStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        encryption_key: kms.IKey,
        lambda_role: iam.IRole,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Amazon Cognito User Pool & Domain for Machine-to-Machine (M2M) OAuth2 Auth
        self.user_pool = cognito.UserPool(
            self,
            "A2AUserPool",
            user_pool_name="ConnectConcierge-A2AUserPool",
            self_sign_up_enabled=False,
            removal_policy=RemovalPolicy.DESTROY
        )

        domain_prefix = "concierge-a2a-mesh-gateway"
        self.user_pool_domain = cognito.UserPoolDomain(
            self,
            "A2AUserPoolDomain",
            user_pool=self.user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=domain_prefix
            )
        )

        # Resource Server & Scopes
        self.resource_server = cognito.UserPoolResourceServer(
            self,
            "A2AResourceServer",
            user_pool=self.user_pool,
            identifier="a2a",
            user_pool_resource_server_name="Agent-to-Agent Mesh Gateway",
            scopes=[
                cognito.ResourceServerScope(
                    scope_name="handoff",
                    scope_description="Initiate A2A agent session handoff"
                ),
                cognito.ResourceServerScope(
                    scope_name="read",
                    scope_description="Read Agent Cards metadata"
                )
            ]
        )

        # App Client with Client Credentials Flow
        self.app_client = cognito.UserPoolClient(
            self,
            "A2AAppClient",
            user_pool=self.user_pool,
            user_pool_client_name="A2AMeshClient",
            generate_secret=True,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    client_credentials=True
                ),
                scopes=[
                    cognito.OAuthScope.custom("a2a/handoff"),
                    cognito.OAuthScope.custom("a2a/read")
                ]
            )
        )
        self.app_client.node.add_dependency(self.resource_server)

        # 2. Lambda Functions for Returns Specialist and A2A Router
        self.returns_specialist_fn = lambda_.Function(
            self,
            "ReturnsSpecialistFunction",
            function_name="ConnectConcierge-ReturnsSpecialist",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambdas.returns_specialist_agent.handler",
            code=lambda_.Code.from_asset(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
            ),
            role=lambda_role,
            timeout=Duration.seconds(10),
            memory_size=256,
            log_group=logs.LogGroup(
                self,
                "ReturnsSpecialistLogGroup",
                log_group_name="/aws/lambda/ConnectConcierge-ReturnsSpecialist",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment={"LOG_LEVEL": "INFO"}
        )

        self.a2a_router_fn = lambda_.Function(
            self,
            "A2ARouterFunction",
            function_name="ConnectConcierge-A2ARouter",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambdas.a2a_router.handler",
            code=lambda_.Code.from_asset(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
            ),
            role=lambda_role,
            timeout=Duration.seconds(10),
            memory_size=256,
            log_group=logs.LogGroup(
                self,
                "A2ARouterLogGroup",
                log_group_name="/aws/lambda/ConnectConcierge-A2ARouter",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment={
                "LOG_LEVEL": "INFO",
                "RETURNS_SPECIALIST_FUNCTION_NAME": self.returns_specialist_fn.function_name
            }
        )

        # Attach explicit policy inside this stack to avoid CDK cross-stack cyclic dependency
        invoke_policy = iam.Policy(
            self,
            "RouterInvokeSpecialistPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[self.returns_specialist_fn.function_arn]
                )
            ]
        )
        invoke_policy.attach_to_role(lambda_role)

        # 3. Serverless API Gateway HTTP API for A2A Gateway
        self.http_api = apigw2.HttpApi(
            self,
            "A2AGatewayHttpApi",
            api_name="ConnectConcierge-A2AGatewayApi",
            description="Serverless A2A Gateway HTTP API for Multi-Agent Collaboration"
        )

        # Configure Stage Rate Limiting (10 req/sec, burst 20) for Cost Abuse Protection
        if self.http_api.default_stage and self.http_api.default_stage.node.default_child:
            cfn_stage: apigw2.CfnStage = self.http_api.default_stage.node.default_child
            cfn_stage.default_route_settings = apigw2.CfnStage.RouteSettingsProperty(
                throttling_rate_limit=10,
                throttling_burst_limit=20
            )

        # Cognito JWT Authorizer
        issuer_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}"
        self.jwt_authorizer = authorizers.HttpJwtAuthorizer(
            "A2ACognitoAuthorizer",
            jwt_issuer=issuer_url,
            jwt_audience=[self.app_client.user_pool_client_id]
        )

        # Integrations
        router_integration = integrations.HttpLambdaIntegration(
            "A2ARouterIntegration",
            self.a2a_router_fn
        )

        specialist_integration = integrations.HttpLambdaIntegration(
            "ReturnsSpecialistIntegration",
            self.returns_specialist_fn
        )

        # Add Routes
        # 1. Public/Card Discovery Route: GET /a2a/agent-cards/{agent_id}
        self.http_api.add_routes(
            path="/a2a/agent-cards/{agent_id}",
            methods=[apigw2.HttpMethod.GET],
            integration=router_integration
        )

        # 2. Secured Handoff Route: POST /a2a/handoff
        self.http_api.add_routes(
            path="/a2a/handoff",
            methods=[apigw2.HttpMethod.POST],
            integration=router_integration,
            authorizer=self.jwt_authorizer
        )

        # 3. Secured Direct Specialist Route: POST /a2a/specialist/returns
        self.http_api.add_routes(
            path="/a2a/specialist/returns",
            methods=[apigw2.HttpMethod.POST],
            integration=specialist_integration,
            authorizer=self.jwt_authorizer
        )

        # Stack Outputs for Verification and Simulation
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.app_client.user_pool_client_id)
        CfnOutput(
            self,
            "TokenEndpointUrl",
            value=f"https://{self.user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com/oauth2/token"
        )
        CfnOutput(self, "A2AGatewayApiEndpoint", value=self.http_api.url or "")
