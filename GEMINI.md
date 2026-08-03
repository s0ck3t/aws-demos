# GEMINI.md: Instructions for Future AI Development Sessions

Welcome, AI coding assistant. This file defines the engineering guidelines, architectural preferences, security protocols, and development workflows for the **AWS Demos** workspace. 

You must read, understand, and adhere to these instructions for all tasks in this repository.

---

## 1. Core Mandates for AI Assistants

Before modifying any code or creating new files:
1.  **Read and Trace**: Scan the existing root `README.md`, project-specific `README.md`, and `architecture.md` files to understand context and established design choices.
2.  **Use Planning Mode**: For any architectural change, complex feature implementation, or infrastructure design, create an `implementation_plan.md` artifact first. Do not make code modifications or run infrastructure commands until the user has approved the plan.
3.  **Use Clickable Links**: Ensure file paths and symbols are written as clickable GitHub-style Markdown links (`file:///absolute/path/to/file` using forward slashes).
4.  **Language & Currency Conventions**: All blog posts, documentation, technical notes, and explanations must consistently use **British English spellings** (e.g. *personalise*, *personalisation*, *centre*, *instalment*, *favour*, *optimise*, *organise*) and **GBP (£)** currency costings (e.g., *£0.00/month baseline cost*, *~£25/month NAT Gateway cost*).

---

## 2. Serverless Cost-Control (Zero-Baseline Pattern)

Because these projects are designed for portfolio demonstrations and low-traffic public sector pilots, we must strictly manage operational cloud costs. 

*   **Avoid Idle Compute Charges**: Never configure resources that bill continuously while sitting idle (e.g. provisioned RDS databases, standard Amazon OpenSearch collections, NAT Gateways, or active Application Load Balancers).
*   **Favour Serverless Equivalents**:
    *   *Vector Stores*: Use **Amazon S3 Vectors** or Pinecone Serverless instead of Amazon OpenSearch Serverless (AOSS) clusters.
    *   *Databases*: Use **Amazon DynamoDB** (on-demand capacity) or **Amazon Aurora Serverless v2** (configured to scale down to 0 ACUs when inactive).
    *   *APIs*: Use serverless **API Gateway HTTP APIs** instead of application-managed load balancers.
    *   *Compute*: Use **AWS Lambda** or **AWS App Runner** (with scale-to-zero configurations) for web hosting.
*   **Avoid NAT Gateways**: In VPC network configurations, avoid NAT Gateways ($32+/month baseline) for internet routing. Instead:
    *   Deploy compute to public subnets if it does not hold sensitive state.
    *   For private resources accessing AWS APIs (like Bedrock or DynamoDB), use **VPC Endpoints (PrivateLink)** to restrict traffic internally, avoiding the NAT Gateway cost.

---

## 3. Security & Well-Architected Framework

Always enforce enterprise-grade security:
1.  **KMS Customer Managed Keys (CMKs)**: All storage (S3, RDS, EBS, SQS) must be encrypted using a dedicated CMK with key rotation enabled. Do not use default AWS-managed keys (`aws/s3`, etc.) as they do not support cross-service resource policies.
2.  **Least-Privilege IAM Policies**: Scope IAM policies tightly. Avoid wildcard permissions (`"Resource": "*"`) for write, update, or read actions. Restrict execution roles (e.g., Lambda execution, Bedrock service role) specifically to the ARNs of resources they manage.
3.  **Secrets Management**: Never write api keys, database passwords, or credentials into code, configuration files, or environment variables. Retrieve secrets dynamically at runtime from **AWS Secrets Manager** or **AWS Systems Manager Parameter Store**.
4.  **Network Isolation**: Keep databases, search indexes, and vector stores in isolated private subnets, allowing access only via security group ingress rules and private endpoints.

---

## 4. Coding & Orchestration Conventions

To align with AWS internal preferences and maintain codebase maintainability:
*   **AWS-Native SDKs (`boto3` / `@aws-sdk`)**: Build RAG pipelines, model queries, and service integrations using the native AWS SDK. Favour native API calls over high-level abstraction frameworks (e.g. LangChain, LlamaIndex) unless the user explicitly requests them. Native SDKs keep dependency trees small and predictable.
*   **IaC Tooling**: Write infrastructure using **AWS Cloud Development Kit (CDK)** in Python. Establish clean Stack segregation:
    *   `SecurityStack`: Manages KMS keys, IAM roles, policies.
    *   `DataStorageStack`: Manages S3 buckets, databases, data sources.
    *   `ComputeStack`: Manages Lambdas, App Runner, ECS tasks.
*   **Clean Separations**:
    *   `/infra` - All CDK code.
    *   `/src` - All application code.
    *   `/tests` - All testing code.

---

## 5. Testing & Validation Workflow

Every project must be accompanied by programmatic validation:
1.  **Unit Tests**: Written using `pytest` to test application helpers, parsers, and logic.
2.  **CDK Assertions**: Validate IaC stacks using standard CDK assertions to check resource counts, encryption rules, and policy attachments.
3.  **Generative AI Evaluation**: Implement offline evaluation suites (using frameworks like **Ragas** or LLM-as-a-judge patterns) to measure retrieval quality and output accuracy against golden test sets. A generative demo is not complete without an accuracy pipeline.

---

## 6. Handoff & Commits
*   Ensure changes are documented. When adding a new demo, update the root `README.md` table of projects and write a dedicated `architecture.md` file in the new project subdirectory.
*   Clearly output manual configuration steps, CDK command prompts, and local environment variables so the user can easily deploy the code.

---

## 7. Engineering Discoveries & Workarounds (Generic)

Keep these key learnings and workarounds in mind during implementation:
*   **S3 Vectors Metadata Limit**: Amazon S3 Vectors limits filterable metadata to 2 KB. Large metadata fields (such as raw text and chunk content) must be explicitly configured as non-filterable (e.g. using `nonFilterableMetadataKeys` in CDK) to prevent ingestion job failures when using hierarchical chunking.
*   **Cross-Stack CDK Cyclic Dependencies**: When granting permissions or referencing resources across separate stacks, instantiate a separate `iam.Policy` inside the dependent stack and call `policy.attach_to_role(...)` rather than using `role.add_to_policy(...)` or `resource.grant_read_write(role)` which causes CloudFormation cyclic loops.
*   **CloudFormation Export Deadlocks**: Replacing or modifying configurations of exported resources (such as changing an S3 Vector Index configuration which triggers resource replacement) will be blocked by CloudFormation if the ARN is imported downstream. Temporarily delete the importing stack, deploy the changes, and redeploy the downstream stack.
*   **KMS Key Policy for Service Principals**: When encrypting storage indexes with a Customer Managed Key (CMK), ensure service principals performing asynchronous background operations (such as `indexing.s3vectors.amazonaws.com`) are granted explicit `kms:Decrypt` and `kms:GenerateDataKey` permissions.
*   **Active Bedrock Models**: Avoid using retired or legacy Bedrock model endpoints (e.g. Claude 3 Haiku for document parser strategy). Ensure the stack utilizes current active endpoints (e.g. Claude 3 Sonnet) for Bedrock platform services.
*   **Local Credential Resolution**: Local application runtimes (e.g., Streamlit, FastAPI) and test suites should resolve credentials dynamically via standard AWS CLI methods (`aws sso login` or standard active AWS profiles) rather than using static access keys.
*   **Customer Profiles CloudFormation Standard Identifiers**: In CloudFormation's `AWS::CustomerProfiles::ObjectType` resource schema (`ObjectTypeKeyProperty`), `StandardIdentifiers` must be specified using valid CloudFormation enum values (such as `["PROFILE"]` or `["UNIQUE"]`) rather than runtime SDK string identifiers (`EMAIL_ADDRESS` / `PHONE_NUMBER`).
*   **Customer Profiles AutoMerging Required Properties**: When `AutoMerging` is set to `enabled=True` in `CfnDomain.MatchingProperty`, CloudFormation requires **BOTH** `consolidation` (`ConsolidationProperty`) AND `conflict_resolution` (`ConflictResolutionProperty`). Omitting `consolidation` causes CloudFormation creation to fail with a `400 InvalidRequest`.
*   **Customer Profiles ObjectType Key Names & Mandatory Identifiers**: In `CfnObjectType.KeyMapProperty`, key names must use predefined Customer Profiles key names (`_email`, `_phone`, `_account`, `_fullName`). Furthermore, CloudFormation requires at least one key with `PROFILE` and exactly one key with `UNIQUE` in `StandardIdentifiers` (e.g., `standard_identifiers=["PROFILE", "UNIQUE"]`).
*   **Customer Profiles Field Content Types for Identity Keys**: Fields mapped to standard identity keys (`_email` or `_phone`) must specify exact matching content types (`"EMAIL_ADDRESS"` and `"PHONE_NUMBER"` respectively). Using `"STRING"` triggers CloudFormation `Defining key with mismatching field types` failures.
*   **Customer Profiles Console UI vs SDK Custom Attribute Visibility**: The default AWS Management Console UI for Customer Profiles only renders built-in standard identity fields (First Name, Last Name, Email, Phone, Account Number) and Calculated Attributes. Custom key-value pairs (`Attributes`) attached via `create_profile` / `update_profile` are stored inside the underlying profile record and accessible via `search_profiles` / `get_profile` API calls, but do not render on the standard out-of-the-box AWS admin console screen without a custom Agent Workspace view or panel.
