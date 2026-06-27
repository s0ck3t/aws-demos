# Sprint 3 Completion Walkthrough: Streamlit Web Interface & Containerization

This document details the successful implementation, testing, and containerization of **Sprint 3** for **The Brentwood Policy Oracle**.

---

## 🚀 Accomplishments & Changes

We have implemented a professional, friendly, and clean Streamlit web application, created a containerized packaging configuration using Docker and Docker Compose, and verified the application's runtime initialization using programmatic integration tests.

### 1. Frontend & Custom Styling
*   **[app.py](../src/app.py)**:
    *   Creates a complete chat UI allowing housing officers and citizens to input policy queries.
    *   Maintains scrollable chat history in the Streamlit `session_state`.
    *   Displays query answers grounded in policy documents.
    *   Renders citation references inside styled, collapsible accordions (`st.expander`) directly below the corresponding assistant response, showing the source filename, page number, and raw text chunk excerpt.
    *   Includes a dynamic sidebar showing active policy documents referenced in the current session.
    *   Supports session reset via a "Clear Conversation History" action.
*   **[style.css](../src/static/style.css)**:
    *   Applies custom branding and aesthetics.
    *   Utilizes the friendly, modern **Outfit** Google Font.
    *   Implements a light, professional, and friendly theme (custom HSL color schema, white background elements, soft grey-blue accents, clear contrast).
    *   Overrides Streamlit elements (hiding default headers/footers) to create an app-like experience.

### 2. Containerization
*   **[Dockerfile](../Dockerfile)**:
    *   Uses the secure, lightweight, and modern **`python:3.13-slim`** base image (matching the local host environment).
    *   Ensures stdout/stderr are unbuffered and disables `.pyc` creation.
    *   Installs dependencies and exposes port `8501`.
    *   Defines a standard health check via `curl` against `http://localhost:8501/_stcore/health`.
*   **[docker-compose.yaml](../docker-compose.yaml)**:
    *   Orchestrates local runtime deployment.
    *   Passes local AWS session authentication parameters from host environments (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.).
    *   Bind-mounts the local `~/.aws` folder into `/root/.aws:ro` to enable seamless AWS credential resolution.

### 3. Integration Testing
*   **[test_app.py](../tests/test_app.py)**:
    *   Launches the Streamlit app on a test-specific port (`8509`) in a background subprocess.
    *   Polls the health check endpoint for up to 10 seconds.
    *   Asserts the endpoint returns `200 OK`.
    *   Terminates the process cleanly after the test finishes.

---

## 🧪 Testing & Validation Results

We executed the test suite to confirm correctness across the CDK infrastructure, orchestration logic, and Streamlit app:
```powershell
.venv\Scripts\pytest.exe
```

*   **Results**: **13/13 Tests Passed** (including 4 CDK infrastructure stack tests, 8 orchestration backend tests, and 1 new app health check integration test).
*   **Verified Controls**:
    *   Streamlit app boots without import errors, resolves all dependencies, and responds successfully to HTTP requests.

---

## 🔍 How to Run Locally

### 1. Running the Streamlit App Directly
Ensure your local terminal has active AWS credentials (e.g. via `aws sso login` or environment variables) and run:
```powershell
.venv\Scripts\streamlit run src/app.py
```

### 2. Running in Docker
Build and launch the application container using Docker Compose. The configuration is pre-configured to inherit your local shell's AWS credentials and profile settings:
```bash
docker compose up --build
```
Once started, visit `http://localhost:8501` to access the application.

---

## 📋 Future Roadmap: Playwright End-to-End Testing

As requested, we will incorporate **Playwright End-to-End Browser Testing** into the upcoming sprint plans:
*   **Objective**: Validate real browser interactions (entering text, clicking submit, verifying the assistant message bubble renders, and expanding the citation accordion).
*   **Approach**: Add `playwright` and `pytest-playwright` dependencies, launch the Streamlit app using a pytest fixture, and use a headless browser to perform behavioral validation of the UI.
