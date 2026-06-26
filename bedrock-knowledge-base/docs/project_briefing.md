# Project Briefing: The Brentwood Policy Oracle

This document serves as the master blueprint for the RAG (Retrieval-Augmented Generation) portfolio piece. It is structured into practical components to prepare for building, filming, and launching the project.

## 1. Executive Summary
The Brentwood Policy Oracle is a proof-of-concept, serverless Retrieval-Augmented Generation (RAG) system designed to act as a secure, high-accuracy conversational interface for public sector documents. Utilizing real-world, publicly available strategies and housing policies from Brentwood Borough Council, the system allows internal staff and local citizens to query dense, complex legal regulations and receive immediate, citation-backed answers.

## 2. Objectives
* **Acknowledge Data Complexity**: Successfully ingest and query unstructured public sector PDFs that contain dense legal guidelines, statutory timelines, and multi-column tables.
* **Prioritize Traceability (No Hallucination)**: Ensure every generated response is strictly grounded in the source data, returning the exact document title, section, and page number to the end-user.
* **Demonstrate Cost-Consciousness**: Explicitly design around default high-cost cloud configurations, creating a pipeline suitable for low-traffic public sector pilots without high baseline infrastructure overhead.
* **Establish Metric-Driven Trust**: Implement a programmatic evaluation strategy to score the system's performance on factual consistency (faithfulness) and answer relevance.
* **Apply AWS Well-Architected Principles**: Implement security-at-all-layers (least-privilege IAM roles, S3 bucket encryption, VPC Private Links) and cost optimization patterns (S3 Vectors storage tiered lifecycle management).

## 3. Core Requirements & Scope

### A. Data Corpus
The target dataset consists of actual, unaltered public documents from Brentwood Borough Council's policy library, representing varied layout styles and technical challenges:
* **Damp, Mould and Condensation Policy**: Highly operational text containing specific service-level agreement (SLA) timelines for inspections and landlord vs. tenant responsibilities.
* **Housing Allocation Policy**: Highly structured document featuring dense tables, eligibility matrices, and banding/points allocation rules for housing applications.
* **Homelessness Strategy / Placement Policy**: Policy documents detailing statutory obligations, temporary accommodation criteria, and legal constraints (e.g., the 6-week placement rule for families).

### B. Functional System Boundaries
The prototype must deliver three core components:
1. **Managed Document Pipeline**: A cloud-based document repository that can ingest raw PDFs, perform optical character recognition (OCR) or smart parsing on complex structures like tables, chunk the data semantically, and index it.
2. **Web-Based User Interface**: A simple, intuitive chat interface that displays:
   * The natural language answer.
   * Collapsible "Source References" showing the exact text excerpt, source document, and page number used to generate the answer.
3. **Automated Testing Suite**: An offline pipeline to evaluate system outputs against a curated golden test set of user queries and baseline answers, providing transparent accuracy metrics before any production deployment.

## 4. Technical Decisions Deferred
To maintain a strict "requirements-first" posture, the following engineering implementations are explicitly deferred to the next phase of architectural design:
* Selection of the specific vector database backend (e.g., Amazon OpenSearch Serverless, S3 Vectors, PGVector, or third-party offerings).
* Exact chunking strategy configurations (e.g., semantic, hierarchical, or parent-child chunking parameters).
* Specific foundation models (LLMs) and text embedding models to be utilized.
* Infrastructure deployment methodologies (Terraform vs. AWS CDK vs. CloudFormation).
* Exact Python orchestration frameworks (e.g., LangChain, LlamaIndex, or native AWS SDK).
