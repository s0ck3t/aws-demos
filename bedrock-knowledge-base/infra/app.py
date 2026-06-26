import os
from aws_cdk import App, Environment
from security_stack import SecurityStack
from data_storage_stack import DataStorageStack
from knowledge_base_stack import KnowledgeBaseStack

app = App()

# Configure environment targeting eu-west-2 (London) by default
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "eu-west-2")
)

# 1. Security Stack (KMS Keys, IAM Roles)
security_stack = SecurityStack(app, "BrentwoodSecurityStack", env=env)

# 2. Data Storage Stack (S3 Buckets, Vector Bucket, Vector Index)
storage_stack = DataStorageStack(
    app, "BrentwoodDataStorageStack",
    kms_key=security_stack.kms_key,
    bedrock_role=security_stack.bedrock_role,
    env=env
)

# 3. Knowledge Base Stack (Bedrock KB, Bedrock Data Source, FM Parser, Chunking)
kb_stack = KnowledgeBaseStack(
    app, "BrentwoodKnowledgeBaseStack",
    kms_key=security_stack.kms_key,
    bedrock_role=security_stack.bedrock_role,
    raw_bucket=storage_stack.raw_bucket,
    vector_bucket=storage_stack.vector_bucket,
    vector_index=storage_stack.vector_index,
    env=env
)

app.synth()
