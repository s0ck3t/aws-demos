"""Catalog Ingestion Lambda Function.

Parses product catalog CSV files uploaded to S3 and ingests items into Customer Profiles object types.
"""

import os
import csv
import json
import logging
import boto3
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

s3_client = boto3.client("s3")
customer_profiles_client = boto3.client("customer-profiles")

DOMAIN_NAME = os.environ.get("CUSTOMER_PROFILES_DOMAIN", "omnichannel_concierge_domain")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler triggered by S3 CSV upload or manual test payload."""
    logger.info(f"Received catalog ingestion event: {json.dumps(event)}")
    
    processed_count = 0
    records = event.get("Records", [])

    for record in records:
        s3_info = record.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name")
        key = s3_info.get("object", {}).get("key")

        if not bucket or not key:
            logger.warning("Event record missing bucket or key info. Skipping.")
            continue

        logger.info(f"Fetching CSV object from s3://{bucket}/{key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        lines = response["Body"].read().decode("utf-8").splitlines()

        reader = csv.DictReader(lines)
        for row in reader:
            sku = row.get("sku")
            if not sku:
                continue

            payload = {
                "SKU": sku,
                "ProductName": row.get("product_name", ""),
                "Category": row.get("category", ""),
                "Price": str(row.get("price", "0.00")),
                "Brand": row.get("brand", "")
            }

            try:
                customer_profiles_client.put_profile_object(
                    DomainName=DOMAIN_NAME,
                    ObjectTypeName="EcommerceProductCatalog",
                    Object=json.dumps(payload)
                )
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to put catalog object for SKU {sku}: {str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Catalog ingestion complete",
            "processed_items": processed_count
        })
    }
