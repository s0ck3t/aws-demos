import os
import sys
import time
import pytest
import requests
import subprocess
from pathlib import Path
from playwright.sync_api import expect

# Add project root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(scope="module")
def streamlit_server():
    """
    Spawns the Streamlit application on a unique port, polls the health endpoint
    until it returns 200 OK, yields the server URL, and cleans up the process afterwards.
    """
    port = "8515"
    server_url = f"http://localhost:{port}"
    health_url = f"{server_url}/_stcore/health"
    
    python_bin = sys.executable
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Launch Streamlit server in the background
    process = subprocess.Popen(
        [
            python_bin,
            "-m",
            "streamlit",
            "run",
            "src/app.py",
            f"--server.port={port}",
            "--server.headless=true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
    )
    
    try:
        success = False
        # Poll health endpoint for up to 15 seconds
        for _ in range(30):
            time.sleep(0.5)
            
            # Check if process exited early
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise RuntimeError(
                    f"Streamlit process exited prematurely with code {process.returncode}.\n"
                    f"STDOUT: {stdout.decode('utf-8', errors='ignore')}\n"
                    f"STDERR: {stderr.decode('utf-8', errors='ignore')}"
                )
            
            try:
                response = requests.get(health_url, timeout=1.0)
                if response.status_code == 200:
                    success = True
                    break
            except requests.exceptions.RequestException:
                continue
                
        if not success:
            raise RuntimeError(f"Streamlit application health check failed at {health_url}")
            
        yield server_url
        
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

def test_e2e_policy_chat(streamlit_server, page):
    """
    End-to-End test case to:
    1. Navigate to the Streamlit app.
    2. Assert page title, header, and input are present.
    3. Enter a question and submit.
    4. Wait for the assistant response and verify it.
    5. Expand the citation expander and verify the PDF reference.
    6. Capture screenshots of key UI states.
    """
    # Create images directory if it doesn't exist
    images_dir = Path(__file__).resolve().parent.parent / "docs" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Set viewport to ensure a high-quality capture
    page.set_viewport_size({"width": 1280, "height": 960})
    
    # 1. Navigate to the app
    page.goto(streamlit_server)
    
    # Wait for the main page container to load
    page.wait_for_selector(".stApp")
    
    # 2. Assert page elements
    # Assert that the page title is correct (Streamlit sets it in the HTML title)
    expect(page).to_have_title("Brentwood Policy Oracle")
    
    # Assert the header is rendered correctly
    header = page.locator(".app-header h1")
    expect(header).to_have_text("🏛️ The Brentwood Policy Oracle")
    
    # Assert the chat input field is present
    chat_input = page.get_by_placeholder("Enter your policy question (e.g., 'What is the policy on pets?')...")
    expect(chat_input).to_be_visible()
    
    # Take screenshot of the initial load state
    page.wait_for_timeout(1000)  # Wait for style animation/rendering
    page.screenshot(path=str(images_dir / "initial_load.png"))
    
    # 3. Enter a test question and submit
    test_question = "Is prior written permission required for a secure tenant to keep a single cat or dog?"
    chat_input.fill(test_question)
    chat_input.press("Enter")
    
    # 4. Wait for the assistant's response bubble to render
    # We wait for the expander block to be visible as it represents completion of generation
    expander = page.locator('div[data-testid="stExpander"]').filter(has_text="Grounded References")
    expander.wait_for(state="visible", timeout=30000)
    
    # Assert assistant response is present and not empty
    chat_messages = page.locator('[data-testid="stChatMessage"]')
    # The first message is user, the second is assistant
    assistant_msg = chat_messages.nth(1)
    expect(assistant_msg).to_be_visible()
    
    # Get response text and assert it is not empty
    # In Streamlit, markdown text is inside a paragraph or markdown div
    assistant_text = assistant_msg.locator("p, div").first.inner_text()
    assert len(assistant_text.strip()) > 0
    assert "cannot find this information" not in assistant_text.lower()
    
    # 5. Click the citation collapsible expander to show sources
    # Streamlit expanders typically use details > summary
    summary_element = expander.locator("summary, [role='button']").first
    summary_element.click()
    
    # Wait for expand animation
    page.wait_for_timeout(1000)
    
    # Assert that the source PDF reference is visible and contains expected text
    expect(expander).to_contain_text("Pets Policy 2025 - 2028.pdf")
    
    # Take screenshot of the post-response state
    page.screenshot(path=str(images_dir / "search_results.png"))
