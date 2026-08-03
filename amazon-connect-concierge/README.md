# Next-Gen Omnichannel E-Commerce AI Concierge

Welcome to the **Next-Gen Omnichannel E-Commerce AI Concierge** demo. This project implements an enterprise-grade GenAI contact centre platform using Amazon Connect, Amazon Bedrock, Model Context Protocol (MCP), Agent-to-Agent (A2A) Gateway, and real-time customer data readiness with Amazon Connect Customer Profiles.

---

## 🚀 4-Part Architecture & Blog Series

| Part | Title & Focus | Key Tech | Baseline Cost | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Part 1** | [**Zero to AI-Ready: Structuring Enterprise Data**](./blogs/part1_zero_to_ai_ready.md) | Customer Profiles, Dynamic Entity Resolution, S3, EventBridge, Predictive Insights | **£0.00 / month (Idle)** | 🟡 Active (Sprint 1) |
| **Part 2** | **Accelerating Agentic Tooling with an Agentic IDE** | Kiro / Antigravity Agentic IDE, Spec-Driven Dev, Custom MCP Server, Bedrock Guardrails | **£0.00 / month (Idle)** | ⚪ Pending |
| **Part 3** | **Cross-Enterprise Collaboration: Serverless A2A Gateway** | Connect Flows, Bedrock Agent Core, A2A Gateway, API Gateway, Cognito | **£0.00 / month (Idle)** | ⚪ Pending |
| **Part 4** | **Production Gatekeeping: Latency & Accuracy Benchmarking** | DynamoDB, CloudWatch, Python Evaluation Harness | **£0.00 / month (Idle)** | ⚪ Pending |

---

## 📂 Project Structure

```text
amazon-connect-concierge/
├── README.md                      # Project setup and overview
├── architecture.md                # System architecture & trade-offs
├── project_roadmap.md             # Detailed roadmap for Parts 1, 2, 3, & 4
├── cdk.json                       # AWS CDK CLI configuration
├── requirements.txt               # Python dependencies
├── .env.example                   # Local environment variable template
├── blogs/                         # Technical blog post series markdown files
│   └── part1_zero_to_ai_ready.md  # Part 1 publication-ready blog post
├── data/                          # Synthetic product catalog & clickstream events
│   ├── catalog.csv
│   └── clickstream_events.json
├── infra/                         # AWS CDK infrastructure stacks (Python)
│   ├── app.py                     # CDK app entry point
│   └── stacks/
│       ├── security_stack.py      # KMS Customer Managed Keys, IAM Roles
│       ├── storage_stack.py       # S3 Buckets, Customer Profiles Domain & Mappings
│       └── compute_stack.py       # Ingestion Lambdas & Contact Flow integrations
├── src/                           # Application logic
│   ├── lambdas/                   # Data ingestion & recommendations APIs
│   └── utils/                     # Boto3 helpers & profile payload parsers
└── tests/                         # Automated test harness
    ├── infra/                     # CDK stack assertion tests
    └── unit/                      # Pytest unit tests for Lambdas and parsers
```

---

## ⚙️ Prerequisites & Deployment

### 1. Python Environment Setup
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Synthesize & Deploy Infrastructure
```bash
cd infra
cdk synth
cdk deploy --all
```

---

## 🔒 Security & Zero-Baseline Cost Architecture
* **Zero Idle Cost**: Built entirely on AWS serverless technologies (Customer Profiles, Lambda, S3, API Gateway). Scales to 0 when inactive.
* **KMS CMK Encryption**: Storage and profile records are encrypted at rest using Customer Managed Keys with rotation enabled.
* **Least-Privilege IAM**: IAM roles are scoped to strict resource ARNs without wildcard write permissions.
