import os
import sys
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# Ensure the bedrock-knowledge-base root directory is in the Python path
# This allows pytest to import the 'infra' module correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
