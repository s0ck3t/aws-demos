# Sprint-by-Sprint Implementation Plan: The Brentwood Policy Oracle

This checklist outlines the phase-by-phase implementation plan for building, testing, and verifying the RAG pipeline. Each sprint delivers a valuable, testable advance.

---

## 🏃‍♂️ Sprint 1: Document Pipeline & Parsing Ingestion
*   **Objective**: Configure AWS storage, security, and Bedrock Knowledge Base infrastructure using S3 Vectors and FM Parser.
*   **Deliverable**: A fully deployed document ingestion system running in AWS `eu-west-2` capable of parsing complex PDF tables.

### Task Checklist
- [ ] Initialize Python virtual environment and CDK project structure in `/infra`.
- [ ] Implement `SecurityStack` (KMS Customer Managed Key, Key Rotation, IAM roles with least-privilege permissions).
- [ ] Implement `DataStorageStack` (Raw S3 Bucket, S3 Vectors Bucket).
- [ ] Implement `KnowledgeBaseStack` (Bedrock KB, Titan Embeddings V2 v1024, FM Parser using Claude 3 Sonnet, Hierarchical Chunking: 200/1000 tokens).
- [ ] Create CDK assertion tests validating KMS encryption and restricted bucket policies.
- [ ] Write a bootstrap script to upload raw Brentwood PDFs to the source S3 bucket and trigger Bedrock sync.

### Measurable Outcomes (Automatic Tests)
*   **CDK Assertions**: Run `pytest tests/test_infra.py` to assert:
    *   S3 buckets have KMS encryption enabled.
    *   No wildcards (`"Resource": "*"`) exist for S3 read/write statements.
*   **Ingestion Status Check**: Running `python tests/verify_ingestion.py` returns `Status: COMPLETE` from the Bedrock Knowledge Base Ingestion API.

---

## 🏃‍♂️ Sprint 2: Chat Orchestration & Citation Processing
*   **Objective**: Build the backend query orchestration logic and citation extraction parser using native `boto3`.
*   **Deliverable**: A backend CLI/Python interface that queries Bedrock and returns fact-grounded responses with extracted document metadata (filename, page numbers).

### Task Checklist
- [ ] Implement query orchestration function using `boto3` Bedrock agent runtime client.
- [ ] Define the prompt templates for Claude 4.5 Sonnet, instructing it to anchor answers strictly to retrieved citations.
- [ ] Create the citation parser library to extract and format citation text, source filenames, and page numbers from Bedrock's API response structure.
- [ ] Set up Bedrock Guardrails for safety filters and confidence boundary.
- [ ] Write unit tests for the citation parser and response formatting logic.

### Measurable Outcomes (Automatic Tests)
*   **Unit Verification**: Run `pytest tests/test_orchestration.py` verifying:
    *   The citation parser correctly identifies files and pages.
    *   Empty context returns the strict confidence threshold warning: *"I cannot find this information in the policy documents."*
*   **Integration Smoke Test**: A mock query fetches context and prints citations without exceptions.

---

## 🏃‍♂️ Sprint 3: Streamlit Interface & Visual Citations
*   **Objective**: Build a clean, professional web UI displaying chat history, generated answers, and a dedicated collapsible panel for PDF references.
*   **Deliverable**: A local Streamlit application integrated with the AWS Bedrock backend, containerized via Docker.

### Task Checklist
- [x] Implement Streamlit dashboard structure in `src/app.py` with custom styling (light-mode professional and friendly theme).
- [x] Integrate session state handling for chat history persistence.
- [x] Add sidebar and collapsible expanders displaying search citations (text excerpt, page number, document source).
- [x] Create a local `Dockerfile` and `docker-compose.yaml` to containerize the app execution.
- [x] Write integration test assertions verifying Streamlit server startup.

### Measurable Outcomes (Automatic Tests)
*   **Build Test**: Running `docker compose build` succeeds.
*   **App Health Check**: pytest runs integration tests that check Streamlit health endpoint (`http://localhost:8509/_stcore/health`) and verify a `200 OK` is returned.

---

## 🏃‍♂️ Sprint 4: Ragas Accuracy Evaluation Suite
*   **Objective**: Build an automated accuracy testing pipeline using Ragas to measure the quality of RAG generations before deploy.
*   **Deliverable**: An offline testing suite that runs the evaluation dataset, evaluates LLM answers, and logs scorecards.

### Task Checklist
- [ ] Create a golden test dataset under `tests/golden_set.json` (20 questions with verified council policy answers and document sources).
- [ ] Implement `tests/eval_pipeline.py` using **Ragas** and Claude 4.5 Sonnet as the evaluator LLM.
- [ ] Configure the evaluation script to calculate:
    *   **Faithfulness** (no hallucinations).
    *   **Answer Relevance** (directly answers the query).
    *   **Context Recall** (retrieved correct passages).
- [ ] Set threshold gate assertions in the test script.

### Measurable Outcomes (Automatic Tests)
*   **Accuracy Evaluation Run**: Running `pytest tests/eval_pipeline.py` passes successfully with metrics logging:
    *   `faithfulness` >= 0.95
    *   `answer_relevance` >= 0.90
    *   `context_recall` >= 0.90

---

## 🏃‍♂️ Sprint 5: Playwright End-to-End Browser Testing
*   **Objective**: Programmatically validate browser rendering, layout accuracy, and interactive chat functionality.
*   **Deliverable**: An E2E browser automation test suite using Playwright.

### Task Checklist
- [ ] Install `playwright` and `pytest-playwright`.
- [ ] Write E2E browser tests under `tests/test_e2e.py` to launch headless Chromium/Firefox/Webkit instances.
- [ ] Simulate user interaction (entering questions, submitting queries, scrolling, clicking citation expanders).
- [ ] Assert correct visual rendering of user and assistant chat bubbles, matching corporate CSS styles.
- [ ] Assert citations are rendered and expandable with correct page references.

### Measurable Outcomes (Automatic Tests)
*   **Browser interaction verification**: Running `pytest tests/test_e2e.py` starts Streamlit, runs Playwright, inputs test queries, clicks elements, and finishes with `3/3 E2E tests passed`.

