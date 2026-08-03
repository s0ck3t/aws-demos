"""Security Stack for Amazon Connect Omnichannel AI Concierge.

Manages KMS Customer Managed Keys (CMKs) and IAM Roles with least-privilege scoping.
"""

from aws_cdk import Stack, Duration, RemovalPolicy
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from constructs import Construct


class SecurityStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. KMS Customer Managed Key (CMK) for Encryption at Rest
        self.encryption_key = kms.Key(
            self,
            "ConciergeKmsKey",
            description="CMK for Amazon Connect Concierge S3 buckets and Customer Profiles domain",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
            pending_window=Duration.days(7)
        )

        self.encryption_key.add_alias("alias/amazon-connect-concierge-key")

        # Key policy statement for Customer Profiles service principal
        self.encryption_key.add_to_resource_policy(
            statement=iam.PolicyStatement(
                sid="AllowCustomerProfilesServiceEncryption",
                effect=iam.Effect.ALLOW,
                principals=[
                    iam.ServicePrincipal("profile.amazonaws.com")
                ],
                actions=[
                    "kms:Decrypt",
                    "kms:GenerateDataKey*",
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:DescribeKey"
                ],
                resources=["*"]
            )
        )

        # 2. Base IAM Role for Ingestion Lambda Functions
        self.lambda_execution_role = iam.Role(
            self,
            "IngestionLambdaExecutionRole",
            role_name="AmazonConnectConcierge-LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Grant KMS decryption & data key generation to Lambda execution role
        self.encryption_key.grant_encrypt_decrypt(self.lambda_execution_role)
