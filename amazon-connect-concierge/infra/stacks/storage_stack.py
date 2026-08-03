"""Storage Stack for Amazon Connect Omnichannel AI Concierge.

Manages KMS-encrypted S3 ingestion buckets and Amazon Connect Customer Profiles Domain.
"""

from aws_cdk import Stack, RemovalPolicy
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_customerprofiles as customerprofiles
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from constructs import Construct


class StorageStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        encryption_key: kms.IKey,
        lambda_role: iam.IRole,
        domain_name: str = "omnichannel_concierge_domain",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.domain_name = domain_name

        # 1. S3 Ingestion Bucket (Encrypted with KMS CMK)
        self.ingestion_bucket = s3.Bucket(
            self,
            "ConciergeIngestionBucket",
            bucket_name=f"connect-concierge-ingest-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Allow Customer Profiles service principal to read/write export objects in S3
        self.ingestion_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCustomerProfilesServiceS3Exporting",
                effect=iam.Effect.ALLOW,
                principals=[
                    iam.ServicePrincipal("profile.amazonaws.com")
                ],
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:GetBucketAcl"
                ],
                resources=[
                    self.ingestion_bucket.bucket_arn,
                    f"{self.ingestion_bucket.bucket_arn}/*"
                ]
            )
        )

        # 3. ObjectType Mapping: EcommerceProductCatalog
        self.catalog_object_type = customerprofiles.CfnObjectType(
            self,
            "CatalogObjectType",
            domain_name=self.domain_name,
            object_type_name="EcommerceProductCatalog",
            description="Catalog object type for product SKUs and category mappings",
            allow_profile_creation=False,
            expiration_days=365,
            fields=[
                customerprofiles.CfnObjectType.FieldMapProperty(name="SKU", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="SKU", target="_profile.Attributes.SKU", content_type="STRING")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="ProductName", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="ProductName", target="_profile.Attributes.ProductName", content_type="STRING")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="Category", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="Category", target="_profile.Attributes.Category", content_type="STRING")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="Price", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="Price", target="_profile.Attributes.Price", content_type="STRING"))
            ],
            keys=[
                customerprofiles.CfnObjectType.KeyMapProperty(
                    name="_account",
                    object_type_key_list=[
                        customerprofiles.CfnObjectType.ObjectTypeKeyProperty(
                            standard_identifiers=["PROFILE", "UNIQUE"],
                            field_names=["SKU"]
                        )
                    ]
                )
            ]
        )

        # 4. ObjectType Mapping: WebClickstreamEvent
        self.clickstream_object_type = customerprofiles.CfnObjectType(
            self,
            "ClickstreamObjectType",
            domain_name=self.domain_name,
            object_type_name="WebClickstreamEvent",
            description="Web clickstream events mapped to customer profile identifiers",
            allow_profile_creation=True,
            expiration_days=365,
            fields=[
                customerprofiles.CfnObjectType.FieldMapProperty(name="EventId", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="EventId", target="_profile.Attributes.EventId", content_type="STRING")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="EmailAddress", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="EmailAddress", target="_profile.EmailAddress", content_type="EMAIL_ADDRESS")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="PhoneNumber", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="PhoneNumber", target="_profile.PhoneNumber", content_type="PHONE_NUMBER")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="EventType", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="EventType", target="_profile.Attributes.EventType", content_type="STRING")),
                customerprofiles.CfnObjectType.FieldMapProperty(name="SKU", object_type_field=customerprofiles.CfnObjectType.ObjectTypeFieldProperty(source="SKU", target="_profile.Attributes.SKU", content_type="STRING"))
            ],
            keys=[
                customerprofiles.CfnObjectType.KeyMapProperty(
                    name="_account",
                    object_type_key_list=[
                        customerprofiles.CfnObjectType.ObjectTypeKeyProperty(
                            standard_identifiers=["PROFILE", "UNIQUE"],
                            field_names=["EventId"]
                        )
                    ]
                ),
                customerprofiles.CfnObjectType.KeyMapProperty(
                    name="_email",
                    object_type_key_list=[
                        customerprofiles.CfnObjectType.ObjectTypeKeyProperty(
                            standard_identifiers=["PROFILE"],
                            field_names=["EmailAddress"]
                        )
                    ]
                ),
                customerprofiles.CfnObjectType.KeyMapProperty(
                    name="_phone",
                    object_type_key_list=[
                        customerprofiles.CfnObjectType.ObjectTypeKeyProperty(
                            standard_identifiers=["PROFILE"],
                            field_names=["PhoneNumber"]
                        )
                    ]
                )
            ]
        )

        # 5. IAM Policy for Lambda role (Decoupled to avoid cyclic dependencies)
        storage_access_policy = iam.Policy(
            self,
            "IngestionStorageAccessPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket"
                    ],
                    resources=[
                        self.ingestion_bucket.bucket_arn,
                        f"{self.ingestion_bucket.bucket_arn}/*"
                    ]
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "profile:PutProfileObject",
                        "profile:GetProfileObjectType",
                        "profile:SearchProfiles",
                        "profile:GetMatches"
                    ],
                    resources=[
                        f"arn:aws:profile:{self.region}:{self.account}:domains/{self.domain_name}",
                        f"arn:aws:profile:{self.region}:{self.account}:domains/{self.domain_name}/*"
                    ]
                )
            ]
        )
        storage_access_policy.attach_to_role(lambda_role)
