# AWS Demos & Architecture Portfolio

Welcome to the AWS Demos Portfolio. This repository hosts a collection of production-grade, cost-efficient, and secure cloud demonstrations. Each project is designed to follow the **AWS Well-Architected Framework**, prioritizing security-at-all-layers, strict cost control (scaling to zero where possible), programmatic testing, and Infrastructure as Code (IaC) automation.

---

## 🚀 Repository Directory

| Project Demo | Description | Tech Stack | Baseline Cost | Status |
| :--- | :--- | :--- | :--- | :--- |
| [**The Brentwood Policy Oracle**](./bedrock-knowledge-base/) | Serverless RAG interface for regulatory documents, parsing tables via Bedrock FM Parser and indexing via S3 Vectors. | Bedrock, S3 Vectors, Streamlit, CDK | **$0.00 / month (Idle)** | ✔️ Active (Sprint 2 Completed) |

---

## 📂 Repository Structure

```text
aws-demos/
├── README.md                     # Main repository guide and setup instructions
├── GEMINI.md                     # AI collaboration rules and development practices
└── bedrock-knowledge-base/       # Demo: Serverless RAG on AWS Bedrock
    ├── README.md                 # Demo-specific setup and walkthrough
    ├── architecture.md           # Deep-dive architecture and design decisions
    ├── docs/                     # Raw public policies and briefing documents
    │   ├── brentwood-housing-policies/  # Target UK council PDF documents
    │   └── project_briefing.md   # Initial project parameters
    ├── infra/                    # AWS CDK (Python) infrastructure stacks
    ├── src/                      # Streamlit application source code
    └── tests/                    # Unit tests & Ragas evaluation script
```

---

## ⚙️ Global Prerequisites & Setup

Before running or deploying any demo in this repository, ensure your local development machine has the following tools installed and configured:

### 1. Tooling Requirements
*   **Python (v3.10+)**: Required for application scripts, orchestration, and CDK code.
*   **Node.js (v18+) & npm**: Required to run the AWS Cloud Development Kit (CDK).
*   **AWS CLI v2**: Set up for cloud credential management.
*   **Docker**: Required to run containerized app workloads and local test environments.

### 2. Install AWS CDK
Install the AWS CDK CLI globally:
```bash
npm install -g aws-cdk
```

### 3. AWS Credentials & Authentication
This repository expects authentication via **AWS IAM Identity Center (AWS SSO)** for secure, short-lived session tokens. Avoid using long-lived IAM access keys.

Configure your AWS profile:
```bash
aws configure sso
```
Once configured, log in to your session:
```bash
aws sso login --profile your-profile-name
```
Set your environment variables in your terminal profile:
```bash
export AWS_PROFILE="your-profile-name"
export AWS_DEFAULT_REGION="eu-west-2"
```

### 4. Bootstrap your AWS Account
If you haven't deployed CDK applications to your target AWS region/account before, you must bootstrap the environment:
```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/YOUR_REGION
```

---

## 🔒 Security Standards

All projects in this repository adhere to the following strict security controls:
1.  **Least-Privilege Roles**: IAM policies explicitly resource-restrict actions. Star (`*`) privileges are forbidden unless required by AWS-internal default templates.
2.  **Encryption at Rest & Transit**: All S3 buckets, queues, and databases use **AWS KMS Customer Managed Keys (CMKs)** with 365-day rotation. TLS 1.3 is enforced on all API communication.
3.  **Credential Safety**: No API keys or secrets are committed to Git. Database credentials and third-party tokens route dynamically through **AWS Secrets Manager**.
4.  **Network Isolation**: Whenever AWS hosting is enabled, resources are provisioned in private subnets, utilizing VPC endpoints to access AWS services privately.

---

## 🧪 Testing & Evaluation

A demo is only as good as its tests. We separate testing into:
*   **Infrastructure Tests**: Synthesized CloudFormation template testing via AWS CDK assertions.
*   **Unit Tests**: Standard Python unit tests using `pytest` for codebase functions.
*   **LLM Quality Tests**: Offline evaluation using **Ragas** (measuring Faithfulness, Answer Relevance, and Context Recall) to prevent hallucinations before code lands in production.

---

## 📄 License
This repository is licensed under the MIT License. See individual demo directories for specific licensing or data attribution details.
