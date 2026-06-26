import os
import sys
from pathlib import Path

# Ensure the project root directory is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestrator import query_policy_oracle

def main():
    # Allow query to be passed as CLI arguments, otherwise prompt for input
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Enter your housing policy query: ").strip()

    if not query:
        print("Error: Query cannot be empty.")
        sys.exit(1)

    print(f"\nQuerying: '{query}'")
    print("Please wait...\n")
    
    try:
        result = query_policy_oracle(query)
        
        print("=" * 60)
        print("ANSWER:")
        print("=" * 60)
        print(result['answer'])
        print()
        
        print("=" * 60)
        print("CITATIONS & REFERENCES:")
        print("=" * 60)
        if result['references']:
            for ref in result['references']:
                print(f"- File: {ref['source_file']} | Page: {ref['page_number']}")
        else:
            print("No citations (out-of-domain query or no relevant policy content found).")
        print("=" * 60)
        
    except Exception as e:
        print(f"Execution Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
