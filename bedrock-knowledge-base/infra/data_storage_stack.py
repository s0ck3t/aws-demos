from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3vectors as s3vectors,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct

class DataStorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, kms_key, bedrock_role, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Raw PDF S3 Bucket
        # Encrypted with Customer Managed Key, public access blocked, SSL enforced
        self.raw_bucket = s3.Bucket(
            self, "RawPDFBucket",
            bucket_name=f"brentwood-policies-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 2. S3 Vector Bucket (L1 Construct)
        # Dedicated container for high-dimensional vector data
        self.vector_bucket = s3vectors.CfnVectorBucket(
            self, "VectorBucket",
            vector_bucket_name=f"brentwood-vectors-{self.account}-{self.region}",
            encryption_configuration=s3vectors.CfnVectorBucket.EncryptionConfigurationProperty(
                sse_type="aws:kms",
                kms_key_arn=kms_key.key_arn
            )
        )
        self.vector_bucket.apply_removal_policy(RemovalPolicy.DESTROY)

        # 3. S3 Vector Index (L1 Construct)
        # Defines index parameters (256 dimensions for Titan Embeddings V2, Cosine similarity)
        self.vector_index = s3vectors.CfnIndex(
            self, "VectorIndex",
            index_name="brentwood-policy-index-v2",
            vector_bucket_arn=self.vector_bucket.attr_vector_bucket_arn,
            data_type="float32",
            dimension=256,
            distance_metric="cosine",
            metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                non_filterable_metadata_keys=[
                    "AMAZON_BEDROCK_TEXT",
                    "AMAZON_BEDROCK_METADATA"
                ]
            ),
            encryption_configuration=s3vectors.CfnIndex.EncryptionConfigurationProperty(
                sse_type="aws:kms",
                kms_key_arn=kms_key.key_arn
            )
        )
        self.vector_index.apply_removal_policy(RemovalPolicy.DESTROY)

        # 4. Create separate IAM Policy and attach to Bedrock role
        # This breaks cross-stack cyclic dependency since the policy resource resides in DataStorageStack
        self.bedrock_storage_policy = iam.Policy(
            self, "BedrockStorageAccessPolicy",
            statements=[
                # Raw S3 Bucket read permissions
                iam.PolicyStatement(
                    actions=["s3:GetObject", "s3:ListBucket"],
                    resources=[
                        self.raw_bucket.bucket_arn,
                        f"{self.raw_bucket.bucket_arn}/*"
                    ]
                ),
                # S3 Vector Bucket read/write permissions
                iam.PolicyStatement(
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "s3:DeleteObject"
                    ],
                    resources=[
                        self.vector_bucket.attr_vector_bucket_arn,
                        f"{self.vector_bucket.attr_vector_bucket_arn}/*"
                    ]
                ),
                # S3 Vector Index API permissions
                iam.PolicyStatement(
                    actions=[
                        "s3vectors:GetVectorBucket",
                        "s3vectors:ListIndexes",
                        "s3vectors:GetIndex",
                        "s3vectors:CreateIndex",
                        "s3vectors:UpdateIndex",
                        "s3vectors:DeleteIndex",
                        "s3vectors:PutVectors",
                        "s3vectors:GetVectors",
                        "s3vectors:DeleteVectors",
                        "s3vectors:QueryVectors"
                    ],
                    resources=[
                        self.vector_bucket.attr_vector_bucket_arn,
                        self.vector_index.attr_index_arn
                    ]
                )
            ]
        )
        self.bedrock_storage_policy.attach_to_role(bedrock_role)

