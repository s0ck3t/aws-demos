import os
import sys
import time
import boto3
from pathlib import Path

def get_job_details():
    # Try reading from the temporary file created by bootstrap script
    info_path = Path(__file__).resolve().parent.parent / ".ingestion_job_info"
    if info_path.exists():
        with open(info_path, "r") as f:
            parts = f.read().strip().split(",")
            if len(parts) == 3:
                return parts[0], parts[1], parts[2]
                
    # Fallback to env variables
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
    ds_id = os.environ.get("DATA_SOURCE_ID")
    job_id = os.environ.get("INGESTION_JOB_ID")
    return kb_id, ds_id, job_id

def main():
    kb_id, ds_id, job_id = get_job_details()
    if not kb_id or not ds_id or not job_id:
        print("Error: Could not retrieve Knowledge Base ID, Data Source ID, and Ingestion Job ID.")
        print("Please run the bootstrap script first or define environment variables:")
        print("  - KNOWLEDGE_BASE_ID")
        print("  - DATA_SOURCE_ID")
        print("  - INGESTION_JOB_ID")
        sys.exit(1)
        
    print(f"Monitoring Ingestion Job ID: {job_id}")
    print(f"Knowledge Base ID: {kb_id}")
    print(f"Data Source ID: {ds_id}")
    
    client = boto3.client('bedrock-agent', region_name='eu-west-2')
    
    # Poll ingestion job status
    print("Polling job status every 10 seconds...")
    while True:
        try:
            res = client.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=ds_id,
                ingestionJobId=job_id
            )
            job = res['ingestionJob']
            status = job['status']
            print(f"Current Status: {status}")
            
            if status == "COMPLETE":
                print("Status: COMPLETE")
                stats = job.get('statistics', {})
                print("Job statistics:")
                print(f"  - Documents Scanned: {stats.get('numberOfDocumentsScanned', 0)}")
                print(f"  - Documents Ingested: {stats.get('numberOfDocumentsIndexed', 0)}")
                print(f"  - Documents Failed: {stats.get('numberOfDocumentsFailed', 0)}")
                sys.exit(0)
            elif status in ["FAILED", "STOPPED"]:
                print(f"Error: Ingestion job ended with status: {status}")
                print(f"Failure Reasons: {job.get('failureReasons', [])}")
                sys.exit(1)
                
        except Exception as e:
            print(f"Error querying ingestion status: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    main()
