from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    CfnOutput,
)
from constructs import Construct

class KnowledgeBaseStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kms_key,
        bedrock_role,
        raw_bucket,
        vector_bucket,
        vector_index,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Configure the Knowledge Base Configuration
        kb_config = bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
            type="VECTOR",
            vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"
            )
        )

        # 2. Configure the S3 Vectors storage backend
        # Connects the KB to the S3 Vector bucket and Vector index
        storage_config = bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
            type="S3_VECTORS",
            s3_vectors_configuration=bedrock.CfnKnowledgeBase.S3VectorsConfigurationProperty(
                vector_bucket_arn=vector_bucket.attr_vector_bucket_arn,
                index_arn=vector_index.attr_index_arn
            )
        )

        # 3. Create the Bedrock Knowledge Base
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self, "BrentwoodPolicyKB",
            name="brentwood-policy-oracle-kb",
            role_arn=bedrock_role.role_arn,
            knowledge_base_configuration=kb_config,
            storage_configuration=storage_config
        )

        # 4. Configure the foundation model parser (Claude 3 Sonnet)
        parsing_config = bedrock.CfnDataSource.ParsingConfigurationProperty(
            parsing_strategy="BEDROCK_FOUNDATION_MODEL",
            bedrock_foundation_model_configuration=bedrock.CfnDataSource.BedrockFoundationModelConfigurationProperty(
                model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            )
        )

        # 5. Configure hierarchical chunking (Parent: 1000 tokens, Child: 200 tokens, Overlap: 40 tokens)
        chunking_config = bedrock.CfnDataSource.ChunkingConfigurationProperty(
            chunking_strategy="HIERARCHICAL",
            hierarchical_chunking_configuration=bedrock.CfnDataSource.HierarchicalChunkingConfigurationProperty(
                level_configurations=[
                    bedrock.CfnDataSource.HierarchicalChunkingLevelConfigurationProperty(max_tokens=1000),
                    bedrock.CfnDataSource.HierarchicalChunkingLevelConfigurationProperty(max_tokens=200)
                ],
                overlap_tokens=40
            )
        )

        vector_ingest_config = bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
            parsing_configuration=parsing_config,
            chunking_configuration=chunking_config
        )

        data_source_config = bedrock.CfnDataSource.DataSourceConfigurationProperty(
            type="S3",
            s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                bucket_arn=raw_bucket.bucket_arn
            )
        )

        # 6. Create the S3 Data Source linked to the Knowledge Base
        self.data_source = bedrock.CfnDataSource(
            self, "BrentwoodPolicyDataSource",
            name="brentwood-policy-data-source-v2",
            knowledge_base_id=self.knowledge_base.attr_knowledge_base_id,
            data_source_configuration=data_source_config,
            vector_ingestion_configuration=vector_ingest_config
        )

        # 7. Stack Outputs for post-deployment integration
        CfnOutput(
            self, "KMSKeyArnOutput",
            value=kms_key.key_arn,
            description="KMS Customer Managed Key ARN"
        )
        CfnOutput(
            self, "RawPDFBucketOutput",
            value=raw_bucket.bucket_name,
            description="Raw S3 PDF Source Bucket Name"
        )
        CfnOutput(
            self, "KnowledgeBaseIdOutput",
            value=self.knowledge_base.attr_knowledge_base_id,
            description="Bedrock Knowledge Base ID"
        )
        CfnOutput(
            self, "DataSourceIdOutput",
            value=self.data_source.attr_data_source_id,
            description="Bedrock Data Source ID"
        )
