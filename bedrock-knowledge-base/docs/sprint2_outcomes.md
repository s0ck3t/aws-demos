# Sprint 2 Completion Walkthrough: Chat Orchestration & Citation Processing

This document details the successful implementation, testing, and verification of **Sprint 2** for the **Brentwood Policy Oracle**.

---

## 🚀 Accomplishments & Changes

We have implemented the backend query orchestration, citation extraction parser, and confidence boundaries for the UK housing policy RAG assistant using native `boto3`.

### 1. Application Components
*   **[citation_parser.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/src/citation_parser.py)**:
    *   Created a parsing utility to extract metadata from Bedrock's `retrieve` API JSON response.
    *   URL-decodes source PDF file paths (e.g., `Pets%20Policy%202025%20-%202028.pdf` -> `Pets Policy 2025 - 2028.pdf`).
    *   Extracts float page numbers (e.g., `3.0`) and safely casts them to standard 1-based integers (e.g., `3`).
    *   Implements metadata deduplication to return unique source documents and pages referenced in order of appearance.
*   **[orchestrator.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/src/orchestrator.py)**:
    *   Orchestrates the RAG flow by combining Bedrock Knowledge Base retrieval with Claude 4.5 Sonnet generation.
    *   Implements dynamic `KNOWLEDGE_BASE_ID` resolution (checking environment variables first, then parsing the local `.ingestion_job_info` bootstrap metadata file).
    *   Integrates the system-defined **Claude 4.5 Sonnet Global Inference Profile** (`global.anthropic.claude-sonnet-4-5-20250929-v1:0`) in `eu-west-2` (London) for grounded answer generation.
    *   Implements a double-layer confidence boundary and safety filter that defaults to *"I cannot find this information in the policy documents."* if out-of-domain.
*   **[__init__.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/src/__init__.py)**:
    *   Establishes `src/` as an importable Python package directory.

---

## 🧪 Testing & Validation Results

### 1. Automated pytest Unit Tests
We wrote a comprehensive test suite in [test_orchestration.py](file:///e:/Development/aws-demos/bedrock-knowledge-base/tests/test_orchestration.py) using `pytest` and `unittest.mock` to verify the logic. We ran the test runner:
```powershell
.venv\Scripts\pytest.exe
```

*   **Results**: **12/12 Tests Passed** (including 4 CDK infrastructure stack tests and 8 orchestration backend tests).
*   **Verified Controls**:
    *   S3 URI filename unquoting.
    *   Metadata page number parsing and casting.
    *   Page reference deduplication order and content mapping.
    *   Dynamic Knowledge Base ID resolution (from env and local bootstrap metadata file).
    *   Confidence boundary checks (empty and low-relevance retrieval results bypass the LLM and return the fallback message).
    *   End-to-end mock orchestration for valid queries.

---

## 💻 CLI & RAG Pipeline Verification

We executed end-to-end queries against the live Amazon Bedrock Knowledge Base to verify RAG responses:

### 1. In-Domain Query Example
*   **Query**: `"What is the policy on pets?"`
*   **Outcome**: Retrieved 4 relevant passages from `Pets Policy 2025 - 2028.pdf` (scores between `0.71` and `0.75`).
*   **Response**: Returned a structured policy layout containing permission requirements, prohibited actions (breeding, selling, hoarding), dog-specific garden/communal guidelines, and repair recharge rules.

### 2. Out-of-Domain Query Example (Confidence Boundary)
*   **Query**: `"What is the capital of France?"`
*   **Outcome**: The orchestrator detected that the maximum search score (`0.55`) fell below the `0.60` confidence threshold.
*   **Response**: Bypassed the LLM call entirely and instantly returned: *"I cannot find this information in the policy documents."* (Citations: 0).

---

## 🔍 How to Verify Manually

You can verify the RAG system's end-to-end functionality using the newly added query CLI utility.

### Step 1: Run unit tests
Confirm that the entire test suite compiles and runs successfully:
```bash
.venv\Scripts\pytest.exe
```

### Step 2: Query the Policy Oracle via CLI
Run standard questions or out-of-domain queries by supplying them as arguments to the test utility:
```bash
# Test 1: Valid In-Domain Query
.venv\Scripts\python.exe scripts/run_query.py "What is the policy on pets?"

# Test 2: Irrelevant / Out-of-Domain Query (Confidence Boundary Check)
.venv\Scripts\python.exe scripts/run_query.py "What is the capital of France?"
```
You can also run `.venv\Scripts\python.exe scripts/run_query.py` without arguments, which will prompt you for interactive text entry.
