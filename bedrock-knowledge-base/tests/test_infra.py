import pytest
from aws_cdk import App, assertions
from infra.security_stack import SecurityStack
from infra.data_storage_stack import DataStorageStack
from infra.knowledge_base_stack import KnowledgeBaseStack

def test_kms_key_rotation_enabled():
    """Assert that the Customer Managed Key (CMK) has key rotation enabled."""
    app = App()
    security = SecurityStack(app, "TestSecurityStack")
    template = assertions.Template.from_stack(security)
    
    template.has_resource_properties("AWS::KMS::Key", {
        "EnableKeyRotation": True
    })

def test_s3_buckets_encryption_and_blocking():
    """Assert that raw S3 bucket uses KMS encryption and blocks public access."""
    app = App()
    security = SecurityStack(app, "TestSecurityStack")
    storage = DataStorageStack(
        app, "TestDataStorageStack",
        kms_key=security.kms_key,
        bedrock_role=security.bedrock_role
    )
    template = assertions.Template.from_stack(storage)
    
    # Assert Raw S3 Bucket is encrypted using KMS key
    template.has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": [
                {
                    "ServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms"
                    }
                }
            ]
        },
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True
        }
    })

def test_s3_vectors_bucket_configuration():
    """Assert that the S3 Vector bucket uses KMS encryption."""
    app = App()
    security = SecurityStack(app, "TestSecurityStack")
    storage = DataStorageStack(
        app, "TestDataStorageStack",
        kms_key=security.kms_key,
        bedrock_role=security.bedrock_role
    )
    template = assertions.Template.from_stack(storage)
    
    template.has_resource_properties("AWS::S3Vectors::VectorBucket", {
        "EncryptionConfiguration": {
            "SseType": "aws:kms"
        }
    })

def test_iam_no_s3_wildcard_resource():
    """Assert that Bedrock Execution Role policies do not contain wildcard S3 resources."""
    app = App()
    security = SecurityStack(app, "TestSecurityStack")
    storage = DataStorageStack(
        app, "TestDataStorageStack",
        kms_key=security.kms_key,
        bedrock_role=security.bedrock_role
    )
    
    # Policy statements added to bedrock_role in other stacks will be synthesized under SecurityStack
    template = assertions.Template.from_stack(security)
    
    policies = template.find_resources("AWS::IAM::Policy")
    for policy_id, policy in policies.items():
        doc = policy["Properties"]["PolicyDocument"]
        statements = doc["Statement"]
        for stmt in statements:
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            
            resources = stmt.get("Resource", [])
            if isinstance(resources, str):
                resources = [resources]
                
            is_s3_or_vector_action = any(
                "s3:" in action.lower() or "s3vectors:" in action.lower()
                for action in actions
            )
            
            if is_s3_or_vector_action:
                # Assert that Resource is NOT "*" (wildcard)
                assert "*" not in resources, f"Wildcard permission found in S3 statement: {stmt}"
