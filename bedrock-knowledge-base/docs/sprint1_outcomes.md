# Sprint 1 Completion Walkthrough: Document Pipeline & Parsing Ingestion

This document details the successful implementation, testing, and verification of **Sprint 1** for the **Brentwood Policy Oracle**.

---

## 🚀 Accomplishments & Changes

We have established the base secure serverless ingestion pipeline for UK housing policy documents in `eu-west-2` (London) using the **AWS Cloud Development Kit (CDK)**.

### 1. Cloud Infrastructure (IaC Stacks)
*   **[security_stack.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/infra/security_stack.py)**:
    *   Provisioned a dedicated **KMS Customer Managed Key (CMK)** with a 365-day rotation policy.
    *   Defined the Amazon Bedrock Service Role with restricted trust policies and permissions.
*   **[data_storage_stack.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/infra/data_storage_stack.py)**:
    *   Created the **Raw PDF S3 Source Bucket** encrypted via the CMK.
    *   Provisioned the **S3 Vectors Bucket** and configured the S3 Vectors Index (`CfnIndex`).
    *   Added metadata indexing exclusions (`nonFilterableMetadataKeys` for text and chunks) to handle the 2 KB S3 Vectors metadata limit.
    *   Separated execution policies to resolve cross-stack cyclic references.
*   **[knowledge_base_stack.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/infra/knowledge_base_stack.py)**:
    *   Defined the **Bedrock Knowledge Base** linked to the S3 Vector store.
    *   Configured the **Data Source Ingestion** with **Hierarchical Chunking** (1000 parent tokens, 200 child tokens) and the **Bedrock Foundation Model Parser** using **Claude 3 Sonnet** (selected because Claude 3 Haiku is marked as legacy/retired for Bedrock parsing).

### 2. Ingestion & Operations
*   **[bootstrap_ingestion.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/scripts/bootstrap_ingestion.py)**: Automated PDF uploads and triggered the Bedrock Data Source sync job.
*   **[verify_ingestion.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/tests/verify_ingestion.py)**: Utility to poll the ingestion status until complete.

---

## 🧪 Testing & Validation Results

### 1. CDK Infrastructure Assertions
We executed the automated assertions suite using `pytest` to verify the security controls:
```powershell
pytest tests/test_infra.py
```
*   **Results**: **4/4 Tests Passed**.
*   **Verified Controls**:
    *   KMS CMK has key rotation enabled.
    *   S3 buckets use KMS customer-managed key encryption.
    *   S3 Vectors backend bucket structure conforms to AWS specifications.
    *   Bedrock Execution Role policies are restricted (no broad S3/KMS wildcard privileges).

### 2. Document Ingestion Sync Validation
Running the ingestion pipeline verified successful data indexing:
*   **Command**: `python scripts/bootstrap_ingestion.py`
*   **Status**: `COMPLETE`
*   **Ingestion Job metrics**:
    *   *Documents Scanned*: 19
    *   *Documents Indexed*: 19
    *   *Documents Failed*: 0

---

## 📸 Ingestion & Deploy Verification

Below are screenshots capturing the successful ingestion and configuration details from the AWS console:

<img src="file:///C:/Users/james/.gemini/antigravity/brain/90257797-4727-4077-8f0b-a7fd129135bb/media__1782485946991.png" alt="Ingestion Job Sync Success" width="100%" />

<img src="file:///C:/Users/james/.gemini/antigravity/brain/90257797-4727-4077-8f0b-a7fd129135bb/media__1782488056073.png" alt="S3 Vectors Index Details" width="100%" />
