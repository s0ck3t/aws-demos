from aws_cdk import (
    Stack,
    aws_kms as kms,
    aws_iam as iam,
)
from constructs import Construct

class SecurityStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. KMS Customer Managed Key (CMK)
        # Enable key rotation as required by security standards
        self.kms_key = kms.Key(
            self, "BrentwoodPolicyOracleKey",
            description="KMS CMK for encrypting the Brentwood Policy Oracle storage",
            enable_key_rotation=True,
            alias="alias/brentwood-policy-oracle-key"
        )

        # Allow S3 Vectors service principal to use the CMK for background indexing
        self.kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowS3VectorsServicePrincipal",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("indexing.s3vectors.amazonaws.com")],
                actions=["kms:Decrypt", "kms:GenerateDataKey"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "aws:SourceAccount": self.account
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:s3vectors:{self.region}:{self.account}:bucket/*"
                    }
                }
            )
        )


        # 2. Bedrock Execution Role
        # Define the IAM role that Bedrock Knowledge Base will assume
        self.bedrock_role = iam.Role(
            self, "BedrockExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="IAM Role for Bedrock Knowledge Base execution",
        )

        # 3. Grant Bedrock model invocation permissions
        # Restrict permissions specifically to the models we are using in the region
        self.bedrock_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-4-5-haiku-20251001-v1:0",
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-4-5-sonnet-20250929-v1:0"
            ]
        ))

        # Grant Bedrock access to the KMS CMK
        self.kms_key.grant_encrypt_decrypt(self.bedrock_role)
