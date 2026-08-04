#!/usr/bin/env python3
"""AWS CDK App entry point for Amazon Connect Omnichannel AI Concierge (Part 1)."""

import os
from aws_cdk import App, Environment
from stacks.security_stack import SecurityStack
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack
from stacks.tooling_stack import ToolingStack

app = App()

# Configure AWS Environment (Region and Account)
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID")),
    region=os.environ.get("CDK_DEFAULT_REGION", os.environ.get("AWS_DEFAULT_REGION", "eu-west-2"))
)

# Stack 1: Security Stack (KMS Keys, Execution Roles)
security_stack = SecurityStack(
    app,
    "ConciergeSecurityStack",
    env=env,
    description="Security & KMS Encryption Stack for Amazon Connect Concierge"
)

# Stack 2: Data Storage Stack (S3 Buckets, Customer Profiles Domain)
storage_stack = StorageStack(
    app,
    "ConciergeStorageStack",
    env=env,
    encryption_key=security_stack.encryption_key,
    lambda_role=security_stack.lambda_execution_role,
    domain_name=os.environ.get("CUSTOMER_PROFILES_DOMAIN", "omnichannel_concierge_domain"),
    description="Storage Stack for S3 Ingestion and Customer Profiles Domain"
)
storage_stack.add_dependency(security_stack)

# Stack 3: Compute Stack (Ingestion & Recommendation Lambda Functions)
compute_stack = ComputeStack(
    app,
    "ConciergeComputeStack",
    env=env,
    ingestion_bucket=storage_stack.ingestion_bucket,
    domain_name=storage_stack.domain_name,
    lambda_role=security_stack.lambda_execution_role,
    description="Compute Stack for Ingestion and Profile Recommendation Lambdas"
)
compute_stack.add_dependency(storage_stack)

# Stack 4: Tooling Stack (API Gateway HTTP APIs and Bedrock Guardrails)
tooling_stack = ToolingStack(
    app,
    "ConciergeToolingStack",
    env=env,
    encryption_key=security_stack.encryption_key,
    lambda_role=security_stack.lambda_execution_role,
    description="Tooling Stack for API Gateway HTTP APIs and Bedrock Guardrails"
)
tooling_stack.add_dependency(security_stack)

app.synth()
