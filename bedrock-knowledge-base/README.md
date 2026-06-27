# The Brentwood Policy Oracle (Serverless RAG Demo)

The **Brentwood Policy Oracle** is a serverless, cost-optimized Retrieval-Augmented Generation (RAG) assistant designed for public housing policy queries. Built using **Amazon Bedrock Knowledge Bases**, it allows housing officers and UK citizens to get immediate answers to complex policy questions, accompanied by exact source PDF page citations.

This demo highlights how to handle unstructured public regulatory documents containing complex tables (like points-banding allocation matrices) and operate a RAG pipeline at **$0/month baseline idle cost**.

For a detailed breakdown of the technical decisions and security posture, see [architecture.md](./architecture.md).

---

## 🌟 Core Features

1.  **Tabular Structure Preservation**: Uses the Amazon Bedrock Foundation Model Parser (Claude 3 Sonnet) to translate multi-column regulatory tables into clean Markdown tables before vector ingestion.
2.  **Zero-Idle Compute Bills**: Leverages the new **Amazon S3 Vectors** storage backend, completely avoiding the ~$345/month baseline cost of Amazon OpenSearch Serverless (AOSS).
3.  **Strict Verification and Citations**: Features clickable references in the UI. If a query is not addressed in the downloaded policy library, the guardrails safely respond that the answer cannot be found.
4.  **Continuous Quality Evaluation**: Includes a Python evaluation pipeline using the **Ragas** framework to programmatically assess RAG accuracy (Faithfulness, Relevance, Recall) against a golden test set.

---

## 📂 Project Directory Structure

```text
bedrock-knowledge-base/
├── README.md                 # This file
├── architecture.md           # Deep-dive architecture and design decisions
├── requirements.txt          # Python dependencies
├── Dockerfile                # Streamlit app container definition (Sprint 3)
├── docker-compose.yaml       # Multi-container local orchestration (Sprint 3)
├── docs/                     # Documentation and ingestion PDFs
│   ├── brentwood-housing-policies/  # Raw PDF policies downloaded
│   ├── download_pdfs.py      # Script to scrape council policies
│   ├── project_briefing.md   # Project briefing parameters
│   ├── sprint1_outcomes.md   # Sprint 1 completion walkthrough
│   ├── sprint2_outcomes.md   # Sprint 2 completion walkthrough
│   ├── sprint3_outcomes.md   # Sprint 3 completion walkthrough
│   └── video_script.md       # Presenter demo transcript
├── infra/                    # AWS CDK IaC (Python)
│   ├── app.py                # CDK entrypoint
│   └── knowledge_base_stack.py # Storage, KMS, IAM, and KB definitions
├── scripts/                  # Helper scripts
│   ├── bootstrap_ingestion.py # Script to upload policies and trigger KB sync
│   └── run_query.py          # Script to run policy queries via CLI
├── src/                      # Streamlit Application & Backend
│   ├── __init__.py           # Package init
│   ├── app.py                # Streamlit web application frontend (Sprint 3)
│   ├── citation_parser.py    # Citation extraction logic (Sprint 2)
│   ├── orchestrator.py       # RAG query orchestrator (Sprint 2)
│   └── static/               # Frontend asset and style directory
│       └── style.css         # Custom friendly light CSS styles (Sprint 3)
└── tests/                    # Verification suite
    ├── conftest.py           # Pytest configurations
    ├── test_app.py           # Streamlit health integration tests (Sprint 3)
    ├── test_infra.py         # Infrastructure unit tests (Sprint 1)
    ├── test_orchestration.py # Orchestrator unit tests (Sprint 2)
    └── verify_ingestion.py   # Ingestion verification script (Sprint 1)
```

---

## ⚙️ Quick Start Setup

### Step 1: Initialize local environment
1. Navigate to this demo directory:
   ```bash
   cd bedrock-knowledge-base
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Download / verify housing policies
The actual policy files are already supplied under `docs/brentwood-housing-policies/`. If you need to re-fetch the latest live policies from the council site, you can run:
```bash
python docs/download_pdfs.py
```

### Step 3: Deploy AWS Infrastructure (CDK)
1. Ensure your AWS credentials are active.
2. Bootstrap your AWS region (required if you haven't deployed CDK stacks in `eu-west-2` before):
   ```bash
   npx aws-cdk bootstrap aws://YOUR_ACCOUNT_ID/eu-west-2
   ```
3. Deploy the infrastructure to your AWS account:
   ```bash
   npx aws-cdk deploy --all --require-approval never
   ```
4. *Important*: Once deployment completes, run the bootstrap script to upload the policy PDFs and start the ingestion job:
   ```bash
   python scripts/bootstrap_ingestion.py
   ```
5. Monitor and verify the ingestion sync job until it completes successfully:
   ```bash
   python tests/verify_ingestion.py
   ```

### Step 4: Run the Streamlit Chat App

#### Option A: Running Directly on Host
1. Authenticate local environment variables or ensure active CLI credentials.
2. Run the application:
   ```bash
   streamlit run src/app.py
   ```
3. The interface will automatically open in your default browser at `http://localhost:8501`.

#### Option B: Running in a Docker Container
1. Ensure you have active AWS session parameters or profile configured in your terminal shell.
2. Spin up the application stack using Docker Compose:
   ```bash
   docker compose up --build
   ```
3. Access the web interface at `http://localhost:8501`. The container automatically maps host credentials from `~/.aws` for AWS API runtime access.

---

## 🧪 Running the Offline Ragas Evaluation

To evaluate system outputs against our golden test dataset of questions:
1. Ensure you have the `KNOWLEDGE_BASE_ID` set in your shell environment.
2. Execute the evaluation suite:
   ```bash
   python tests/eval_pipeline.py
   ```
3. The script will retrieve context, generate answers using Claude 4.5 Sonnet, evaluate faithfulness/relevance, and print a consolidated Markdown scorecard to stdout.
