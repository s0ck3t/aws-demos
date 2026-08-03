"""Local Simulation & Verification Script for Part 1.

Simulates customer product catalog ingestion, streaming clickstream events,
and retrieves Customer Profile recommendations payload for GenAI IVR prompt integration.
"""

import os
import sys
import json
import logging

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from lambdas.clickstream_processor import handler as process_clickstream
from lambdas.profile_recommendations import handler as get_recommendations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SimulateCustomerJourney")


def run_simulation():
    logger.info("=" * 60)
    logger.info("STARTING SIMULATION: Next-Gen Omnichannel E-Commerce Concierge")
    logger.info("=" * 60)

    # 1. Load Synthetic Clickstream Data
    clickstream_path = os.path.join(os.path.dirname(__file__), "..", "data", "clickstream_events.json")
    with open(clickstream_path, "r") as f:
        events = json.load(f)

    logger.info(f"\n[STEP 1] Ingesting {len(events)} real-time clickstream events into Customer Profiles...")
    for idx, evt in enumerate(events, 1):
        logger.info(f" -> Event {idx}: Customer '{evt['email']}' performed '{evt['event_type']}' on SKU '{evt['sku']}'")
        # In local offline mode, simulate Lambda invocation
        res = process_clickstream({"detail": evt}, None)
        logger.info(f"    Status: {res['statusCode']} | Response: {res['body']}")

    # 2. Simulate Amazon Connect Contact Flow Invocation
    logger.info("\n[STEP 2] Simulating Amazon Connect IVR Incoming Call...")
    test_phone = "+15550199"
    test_email = "alex.dev@example.com"
    logger.info(f" -> Incoming Caller Phone: {test_phone} (Stitched with Email: {test_email})")

    connect_event = {
        "Details": {
            "Parameters": {
                "Phone": test_phone,
                "Email": test_email
            }
        }
    }

    recommendation_output = get_recommendations(connect_event, None)

    logger.info("\n[STEP 3] Retreived GetProfileRecommendations Payload for GenAI Context:")
    logger.info("-" * 60)
    print(json.dumps(recommendation_output, indent=2))
    logger.info("-" * 60)
    logger.info("\n✅ SIMULATION COMPLETED SUCCESSFULLY! Part 1 Pipeline Ready.")


if __name__ == "__main__":
    run_simulation()
