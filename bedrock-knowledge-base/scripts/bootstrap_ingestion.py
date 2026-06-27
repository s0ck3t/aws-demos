import os
import sys
import glob
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

def discover_cdk_outputs():
    """Discover S3 bucket and KB/DS IDs from deployed CloudFormation stacks."""
    cfn = boto3.client('cloudformation', region_name='eu-west-2')
    stack_name = "BrentwoodKnowledgeBaseStack"
    outputs = {}
    try:
        response = cfn.describe_stacks(StackName=stack_name)
        for output in response['Stacks'][0].get('Outputs', []):
            outputs[output['OutputKey']] = output['OutputValue']
    except Exception as e:
        print(f"Warning: Could not discover outputs from CloudFormation stack '{stack_name}': {e}")
        print("Falling back to environment variables...")
    return outputs

def main():
    print("Starting Brentwood Policy Oracle Bootstrapping...")
    
    # 1. Discover stack resources
    outputs = discover_cdk_outputs()
    bucket_name = os.environ.get("RAW_PDF_BUCKET") or outputs.get("RawPDFBucketOutput")
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID") or outputs.get("KnowledgeBaseIdOutput")
    ds_id = os.environ.get("DATA_SOURCE_ID") or outputs.get("DataSourceIdOutput")
    
    if not bucket_name or not kb_id or not ds_id:
        print("Error: Could not determine S3 Bucket Name, Knowledge Base ID, or Data Source ID.")
        print("Please ensure the CDK stack is deployed or set the following environment variables:")
        print("  - RAW_PDF_BUCKET")
        print("  - KNOWLEDGE_BASE_ID")
        print("  - DATA_SOURCE_ID")
        sys.exit(1)
        
    print(f"Target Raw S3 Bucket: {bucket_name}")
    print(f"Target Knowledge Base ID: {kb_id}")
    print(f"Target Data Source ID: {ds_id}")
    
    # 2. Upload raw PDF files
    # Find all PDFs in docs/brentwood-housing-policies
    pdf_dir = Path(__file__).resolve().parent.parent / "docs" / "brentwood-housing-policies"
    pdf_files = glob.glob(str(pdf_dir / "*.pdf"))
    
    if not pdf_files:
        print(f"Error: No PDF files found in {pdf_dir}")
        sys.exit(1)
        
    s3_client = boto3.client('s3', region_name='eu-west-2')
    print(f"Found {len(pdf_files)} PDF policies to upload.")
    
    for pdf_path_str in pdf_files:
        pdf_path = Path(pdf_path_str)
        key = pdf_path.name
        print(f"Uploading {key}...")
        try:
            s3_client.upload_file(str(pdf_path), bucket_name, key)
        except Exception as e:
            print(f"Failed to upload {key}: {e}")
            sys.exit(1)
            
    print("All PDFs successfully uploaded to S3.")
    
    # 3. Trigger Bedrock Knowledge Base Ingestion Sync Job
    print("Triggering Bedrock Knowledge Base Ingestion Job...")
    bedrock_agent = boto3.client('bedrock-agent', region_name='eu-west-2')
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id
        )
        job = response['ingestionJob']
        print(f"Successfully started ingestion job: {job['ingestionJobId']}")
        print(f"Current Job Status: {job['status']}")
        
        # Save the job information locally for verification script
        # Write to a temporary file
        job_info_path = Path(__file__).resolve().parent.parent / ".ingestion_job_info"
        with open(job_info_path, "w") as f:
            f.write(f"{kb_id},{ds_id},{job['ingestionJobId']}")
            
    except Exception as e:
        print(f"Failed to trigger Bedrock Ingestion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
