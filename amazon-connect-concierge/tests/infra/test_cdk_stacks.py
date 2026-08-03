import os
import sys
import pytest
import aws_cdk as cdk
from aws_cdk import assertions

# Add amazon-connect-concierge root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from infra.stacks.security_stack import SecurityStack
from infra.stacks.storage_stack import StorageStack
from infra.stacks.compute_stack import ComputeStack


def test_security_stack_kms_and_iam():
    app = cdk.App()
    security_stack = SecurityStack(app, "TestSecurityStack")
    template = assertions.Template.from_stack(security_stack)

    # 1. Verify KMS CMK with rotation enabled
    template.has_resource_properties("AWS::KMS::Key", {
        "EnableKeyRotation": True
    })

    # 2. Verify Lambda execution role creation
    template.has_resource_properties("AWS::IAM::Role", {
        "RoleName": "AmazonConnectConcierge-LambdaExecutionRole"
    })


def test_storage_stack_s3_and_customer_profiles():
    app = cdk.App()
    security_stack = SecurityStack(app, "TestSecurityStack")
    storage_stack = StorageStack(
        app,
        "TestStorageStack",
        encryption_key=security_stack.encryption_key,
        lambda_role=security_stack.lambda_execution_role
    )
    template = assertions.Template.from_stack(storage_stack)

    # 1. Verify S3 Bucket Encryption with KMS
    template.has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": [
                {
                    "ServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms"
                    }
                }
            ]
        }
    })

    # 2. Verify ObjectType Mappings (Catalog & Clickstream)
    template.resource_count_is("AWS::CustomerProfiles::ObjectType", 2)


def test_compute_stack_lambdas():
    app = cdk.App()
    security_stack = SecurityStack(app, "TestSecurityStack")
    storage_stack = StorageStack(
        app,
        "TestStorageStack",
        encryption_key=security_stack.encryption_key,
        lambda_role=security_stack.lambda_execution_role
    )
    compute_stack = ComputeStack(
        app,
        "TestComputeStack",
        ingestion_bucket=storage_stack.ingestion_bucket,
        domain_name=storage_stack.domain_name,
        lambda_role=security_stack.lambda_execution_role
    )
    template = assertions.Template.from_stack(compute_stack)

    # Verify 3 Lambda functions (Catalog Ingest, Clickstream Process, Profile Recommendations)
    template.resource_count_is("AWS::Lambda::Function", 3)
