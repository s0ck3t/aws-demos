# Sprint 5 Outcomes: Playwright End-to-End Browser Testing

## Executive Summary

Sprint 5 successfully completes the **Playwright End-to-End Browser Testing** phase for **The Brentwood Policy Oracle**. A robust browser automation test suite has been established, allowing the application to be validated programmatically from user input to frontend rendering, including dynamic interactions (expanding collapsible citations) and grounding verification.

All requirements for Sprint 5 have been fully met:
*   **Dependency Setup**: Playwright and Pytest-Playwright successfully installed and added to `requirements.txt`.
*   **Subprocess Orchestration**: Implemented a reusable pytest fixture that programmatically spawns the Streamlit server on port `8515`, verifies its health at `/_stcore/health`, and ensures clean process termination.
*   **Dynamic Flow Assertions**: Developed browser tests that navigate the UI, input policy queries, await response rendering, expand citations, and assert page content and citations.
*   **Visual Evidence Capture**: Captured high-resolution screenshots of the initial and final states of the web UI to serve as professional portfolio artifacts.
*   **Zero-Regression Verification**: The entire suite, including infrastructure unit tests, orchestrator unit tests, Streamlit app health checks, and E2E browser tests, passes successfully in **11.42 seconds**.

---

## Technical Implementation Details

### 1. Pytest Background Streamlit Fixture
To decouple testing from manual server instantiation, a scoped fixture spawns a headless Streamlit server on port `8515`. The server health check is polled programmatically:
```python
@pytest.fixture(scope="module")
def streamlit_server():
    # Spawns 'streamlit run src/app.py --server.port=8515 --server.headless=true'
    # Polls 'http://localhost:8515/_stcore/health'
    # Yields server URL
    # Terminates/kills background process in finally block
```

### 2. Playwright Flow & Assertions
Using the Playwright `page` fixture, the tests execute the following sequence:
1.  **Load App**: Navigate to `http://localhost:8515`.
2.  **Verify Setup**: Validate webpage title matches `Brentwood Policy Oracle` and header displays `🏛️ The Brentwood Policy Oracle`.
3.  **Submit Query**: Find the chat input textbox, type: *"Is prior written permission required for a secure tenant to keep a single cat or dog?"*, and submit by simulating the `Enter` key.
4.  **Await Response**: Wait for the citation expander (`div[data-testid="stExpander"]` with text `"Grounded References"`) to become visible.
5.  **Assert Output**: Extract the assistant's reply and verify it is not empty or defaulting to a fallback message.
6.  **Verify Grounding**: Click on the expander header using a summary selector (`expander.locator("summary, [role='button']").first.click()`) and assert that the text contains `Pets Policy 2025 - 2028.pdf`.
7.  **Visual Captures**: Automatically save UI screenshots to `docs/images/` at key steps.

---

## UI Screenshots Captured

During the headless test run, the following snapshots are generated:

### 1. Initial Page Load (`initial_load.png`)
Shows the application state upon navigation, showcasing the custom typography and clean, light-themed professional layout with blue accents:
![Initial Load State](../docs/images/initial_load.png)

### 2. Search Results with Expanded Citations (`search_results.png`)
Shows the screen after executing the query. The user message, Claude 4.5 Sonnet response, and expanded references list are fully rendered:
![Search Results State](../docs/images/search_results.png)

---

## How to Execute the E2E Test Suite

Ensure the local virtual environment is active, then execute:

```powershell
# Install browser binaries (first-time setup)
.venv\Scripts\playwright install

# Run only E2E tests
.venv\Scripts\pytest tests/test_e2e.py

# Run all project tests (Unit, Integration, and E2E)
.venv\Scripts\pytest
```
