# Phase 2B Continuation Prompt: Spec-Driven Post-MCP Development

Use this prompt in a new chat session (or subagent invocation) after Phase 2A (MCP Server & Tool Specs setup) has been completed.

---

## 🎯 Goal
Execute **Phase 2B of the Amazon Connect GenAI Concierge series**. You will use the active **Model Context Protocol (MCP) server** (`ecommerce_tooling`), registered in Antigravity (`C:\Users\james\.gemini\config\mcp_config.json`), and OpenAPI specs (`src/schemas/`) to **drive the implementation** of backend Lambda tools, CDK infrastructure (`ToolingStack` with API Gateways and Bedrock Guardrails), unit/CDK test suites, and the Part 2 technical blog post.

---

## 📋 Context & Active MCP Server
The tool specs and MCP server have already been established and installed in Antigravity:
1. **Registered MCP Server**: `ecommerce_tooling` in [`C:\Users\james\.gemini\config\mcp_config.json`](file:///C:/Users/james/.gemini/config/mcp_config.json)
2. **MCP Server Script**: [`src/mcp/mcp_server.py`](file:///E:/Development/aws-demos/amazon-connect-concierge/src/mcp/mcp_server.py)
3. **OpenAPI Schemas**: [`src/schemas/inventory_openapi.json`](file:///E:/Development/aws-demos/amazon-connect-concierge/src/schemas/inventory_openapi.json) & [`src/schemas/ticketing_openapi.json`](file:///E:/Development/aws-demos/amazon-connect-concierge/src/schemas/ticketing_openapi.json)

---

## 🛠️ Tasks for Phase 2B

### Step 1: Inspect MCP Contract
Read and inspect the MCP server definitions in `src/mcp/mcp_server.py` to extract the tool signatures:
* `check_inventory(sku: str)`
* `create_support_ticket(customer_id: str, issue_category: str, description: str, order_id: str = None)`

### Step 2: Implement Backend Tool Lambdas
Using the MCP contract as the source of truth, implement:
1. `src/lambdas/inventory_tool.py`: Lambda handler supporting both API Gateway HTTP API calls (`GET /inventory/{sku}`) and Bedrock Action Group payload formats.
2. `src/lambdas/ticketing_tool.py`: Lambda handler supporting both API Gateway HTTP API calls (`POST /tickets/create`) and Bedrock Action Group payload formats.

### Step 3: Implement CDK ToolingStack (`infra/stacks/tooling_stack.py`)
Provision the infrastructure with **£0.00 baseline idle cost**:
* **API Gateway HTTP APIs**: Route `/inventory/{sku}` (GET) and `/tickets/create` (POST).
* **Amazon Bedrock Guardrail (`CfnGuardrail`)**:
  * Encryption: `kms_key_arn` referencing `SecurityStack` Customer Managed Key.
  * PII Policy: `ANONYMIZE` for email, phone, UK National Insurance numbers; `BLOCK` for credit card & SSN.
  * Topic Policy: `DENY` for unauthorised financial/legal advice and competitor comparisons.
  * Grounding Policy: `GROUNDING` threshold 0.85, `RELEVANCE` threshold 0.80.
  * Version: `CfnGuardrailVersion`.
* **App Entrypoint**: Instantiate `ToolingStack` in `infra/app.py`.

### Step 4: Write Test Suite
* `tests/unit/test_tools.py`: Unit tests for inventory logic, ticketing logic, and MCP stdio handlers.
* `tests/infra/test_tooling_stack.py`: CDK assertion tests validating Lambda count, HTTP API routes, and Bedrock Guardrail properties.

### Step 5: Technical Blog Post
Write `blogs/part2_agentic_tooling_mcp_guardrails.md`:
* Detail the **Spec-Driven, MCP-Led Development Paradigm**.
* Use British English spellings (*personalise*, *anonymise*, *favour*, *centre*) and GBP (£) zero-baseline costings.
* Embed code snippets matching the exact codebase.

---

## 🧪 Verification Commands
After completing the code, run:
```bash
# Run test suite
.venv\Scripts\python.exe -m pytest tests/

# Synthesize CDK stacks
npx cdk synth
```
