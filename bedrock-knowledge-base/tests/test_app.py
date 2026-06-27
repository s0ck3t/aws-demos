import os
import sys
import time
import requests
import subprocess

def test_streamlit_app_health():
    """
    Integration test to verify that the Streamlit application builds,
    starts successfully, and returns a 200 OK on its health check endpoint.
    """
    port = "8509"
    health_url = f"http://localhost:{port}/_stcore/health"
    
    # Path to the active virtual environment python executable
    python_bin = sys.executable
    
    # Project root directory where src/ is located
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # Launch the Streamlit application as a background subprocess
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
        # Poll the health check endpoint for up to 10 seconds
        for _ in range(20):
            time.sleep(0.5)
            
            # If the process died, fail early and read stdout/stderr for diagnostics
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
                # Server is not up yet, continue polling
                continue
                
        assert success, f"Streamlit application health check failed at {health_url}"
        
    finally:
        # Cleanly terminate the subprocess and wait for cleanup
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
