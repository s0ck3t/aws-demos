"""Compute Stack for Amazon Connect Omnichannel AI Concierge.

Manages Python 3.11 Lambda functions for catalog ingestion, event processing, and profile recommendations.
"""

import os
from aws_cdk import Stack, Duration, RemovalPolicy
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

LAMBDA_ASSET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "lambdas"))


class ComputeStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        ingestion_bucket: s3.IBucket,
        domain_name: str,
        lambda_role: iam.IRole,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Common Lambda Environment Variables
        common_env = {
            "CUSTOMER_PROFILES_DOMAIN": domain_name,
            "INGESTION_BUCKET_NAME": ingestion_bucket.bucket_name,
            "LOG_LEVEL": "INFO"
        }

        # 1. Catalog Ingestion Lambda Function
        self.catalog_ingestion_fn = lambda_.Function(
            self,
            "CatalogIngestFunction",
            function_name="ConnectConcierge-CatalogIngest",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="catalog_ingestion.handler",
            code=lambda_.Code.from_asset(LAMBDA_ASSET_DIR),
            role=lambda_role,
            timeout=Duration.seconds(30),
            log_group=logs.LogGroup(
                self,
                "CatalogIngestLogGroup",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment=common_env
        )

        # 2. Clickstream Event Processor Lambda Function
        self.clickstream_processor_fn = lambda_.Function(
            self,
            "ClickstreamProcessFunction",
            function_name="ConnectConcierge-ClickstreamProcess",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="clickstream_processor.handler",
            code=lambda_.Code.from_asset(LAMBDA_ASSET_DIR),
            role=lambda_role,
            timeout=Duration.seconds(15),
            log_group=logs.LogGroup(
                self,
                "ClickstreamProcessLogGroup",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment=common_env
        )

        # 3. Profile Recommendations Lambda Function (Connect Contact Flow helper)
        self.profile_recommendations_fn = lambda_.Function(
            self,
            "ProfileRecommendationsFunction",
            function_name="ConnectConcierge-ProfileRecommendations",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="profile_recommendations.handler",
            code=lambda_.Code.from_asset(LAMBDA_ASSET_DIR),
            role=lambda_role,
            timeout=Duration.seconds(10),
            log_group=logs.LogGroup(
                self,
                "ProfileRecsLogGroup",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY
            ),
            environment=common_env
        )
